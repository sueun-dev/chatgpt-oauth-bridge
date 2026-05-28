from __future__ import annotations

import asyncio
import base64
import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx
import websockets

from codex_oauth import (
    CODEX_BASE_URL,
    choose_image_host_model,
    choose_runtime_source,
    choose_text_model,
    codex_headers,
    codex_openai_client,
    fetch_codex_models,
    load_sources,
)
from run_oauth_matrix import sanitize_response_text


CHATGPT_BACKEND_BASE = "https://chatgpt.com/backend-api"
CODEX_REASONING = {"effort": "xhigh"}
IMAGE_GENERATION_QUALITY = "high"


class OpenAIOAuthAccess:
    """Small OAuth-only wrapper over the surfaces that passed on this machine."""

    def __init__(self) -> None:
        self.sources = load_sources()
        self.source = choose_runtime_source(self.sources)
        self.access_token = self.source.access_token or ""
        self.model_ids = fetch_codex_models(self.access_token)
        self.text_model = choose_text_model(self.model_ids)
        self.image_host_model = choose_image_host_model(self.model_ids)

    def _codex_client(self):
        return codex_openai_client(self.access_token)

    def _response_text_and_types(self, response: Any) -> tuple[str, list[str]]:
        output_text = self._item_get(response, "output_text", "") or ""
        output_types: list[str] = []
        chunks: list[str] = []
        for item in self._item_get(response, "output", []) or []:
            item_type = self._item_get(item, "type")
            if item_type:
                output_types.append(str(item_type))
            for content in self._item_get(item, "content", []) or []:
                text = self._item_get(content, "text")
                if isinstance(text, str):
                    chunks.append(text)
        if not output_text and chunks:
            output_text = "\n".join(chunks)
        return output_text, output_types

    def _item_get(self, obj: Any, key: str, default: Any = None) -> Any:
        value = getattr(obj, key, None)
        if value is None and isinstance(obj, dict):
            value = obj.get(key, default)
        return value if value is not None else default

    def codex_text(self, prompt: str, *, instructions: str = "Answer directly.") -> str:
        text, _ = self._stream_codex_response(
            model=self.text_model,
            instructions=instructions,
            input_payload=[{
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }],
        )
        return text

    def codex_vision(self, image_path: Path | str, prompt: str) -> str:
        path = Path(image_path)
        data_url = f"data:image/png;base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
        text, _ = self._stream_codex_response(
            model=self.text_model,
            instructions="Answer image questions briefly and literally.",
            input_payload=[{
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url},
                ],
            }],
        )
        return text

    def _stream_codex_response(self, *, model: str, instructions: str, input_payload: list[dict[str, Any]]) -> tuple[str, list[str]]:
        text_deltas: list[str] = []
        output_types: list[str] = []
        final_text = ""
        payload = {
            "model": model,
            "store": False,
            "stream": True,
            "reasoning": CODEX_REASONING,
            "instructions": instructions,
            "input": input_payload,
        }
        for event in self._iter_codex_sse_events(payload):
            event_type = str(event.get("type") or "")
            if event_type == "response.output_text.delta":
                delta = event.get("delta")
                if isinstance(delta, str):
                    text_deltas.append(delta)
            elif event_type == "response.output_text.done":
                text = event.get("text")
                if isinstance(text, str):
                    final_text = text
            elif event_type == "response.output_item.done":
                item = event.get("item")
                item_type = item.get("type") if isinstance(item, dict) else None
                if isinstance(item_type, str):
                    output_types.append(item_type)
            elif event_type in {"response.done", "response.completed"}:
                response = event.get("response")
                if isinstance(response, dict):
                    parsed_text, parsed_types = self._response_text_and_types(response)
                    if parsed_text:
                        final_text = parsed_text
                    output_types.extend(parsed_types)
        text = final_text or "".join(text_deltas).strip()
        return text, output_types or (["message"] if text else [])

    def codex_generate_image(self, prompt: str, output_path: Path | str, *, size: str = "1024x1024") -> Path:
        path = Path(output_path)
        image_b64 = None
        if size not in {"1024x1024", "1536x1024", "1024x1536", "auto"}:
            raise ValueError("size must be one of 1024x1024, 1536x1024, 1024x1536, auto")
        payload = {
            "model": self.image_host_model,
            "store": False,
            "stream": True,
            "reasoning": CODEX_REASONING,
            "instructions": "Use the image_generation tool to fulfill this request. Return the generated image.",
            "input": [{
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }],
            "tools": [{
                "type": "image_generation",
                "model": "gpt-image-2",
                "size": size,
                "quality": IMAGE_GENERATION_QUALITY,
            }],
            "tool_choice": {"type": "image_generation"},
        }
        for event in self._iter_codex_sse_events(payload):
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "image_generation_call":
                result = item.get("result")
                if isinstance(result, str) and result:
                    image_b64 = result
            response = event.get("response")
            if isinstance(response, dict):
                for output in response.get("output") or []:
                    if isinstance(output, dict) and output.get("type") == "image_generation_call":
                        result = output.get("result")
                        if isinstance(result, str) and result:
                            image_b64 = result
        if not image_b64:
            raise RuntimeError("No image_generation_call result was returned.")
        path.write_bytes(base64.b64decode(image_b64))
        return path

    def _iter_codex_sse_events(self, payload: dict[str, Any]):
        url = f"{CODEX_BASE_URL}/responses"
        headers = codex_headers(self.access_token)
        with httpx.Client(timeout=httpx.Timeout(600.0)) as client:
            with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code >= 400:
                    raise RuntimeError(f"Codex response failed with HTTP {response.status_code}: {sanitize_response_text(response.read().decode('utf-8', errors='replace'))}")
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    raw = line.removeprefix("data: ").strip()
                    if raw == "[DONE]":
                        break
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(event, dict):
                        yield event

    def official_transcribe_audio(self, audio_path: Path | str, *, model: str = "gpt-4o-mini-transcribe") -> Dict[str, Any]:
        path = Path(audio_path)
        with path.open("rb") as fh:
            files = {
                "file": (path.name, fh, "audio/wav"),
                "model": (None, model),
            }
            return self.official_post("/v1/audio/transcriptions", files=files)

    def official_embedding(self, text: str, *, model: str = "text-embedding-3-small") -> Dict[str, Any]:
        return self.official_post("/v1/embeddings", json_body={"model": model, "input": text})

    def chatgpt_upload_file(self, file_path: Path | str, *, include_download_url: bool = False) -> Dict[str, Any]:
        """Upload a local file through ChatGPT/Codex OAuth file storage.

        This is the same `backend-api/files` flow used by Codex Apps MCP file
        parameters. Signed download URLs are intentionally omitted unless the
        caller asks for one in-memory.
        """
        path = Path(file_path)
        size = path.stat().st_size
        create_url = f"{CHATGPT_BACKEND_BASE}/files"
        headers = codex_headers(self.access_token)
        headers["Content-Type"] = "application/json"
        with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
            create = client.post(create_url, headers=headers, json={
                "file_name": path.name,
                "file_size": size,
                "use_case": "codex",
            })
            payload = self._decode_json_response(create)
            if create.status_code >= 400:
                return payload
            file_id = payload.get("file_id")
            upload_url = payload.get("upload_url")
            if not isinstance(file_id, str) or not isinstance(upload_url, str):
                raise RuntimeError("ChatGPT file create response did not include file_id/upload_url.")
            upload = client.put(
                upload_url,
                headers={
                    "x-ms-blob-type": "BlockBlob",
                    "Content-Length": str(size),
                },
                content=path.read_bytes(),
            )
            if upload.status_code >= 400:
                return {
                    "_http_status": upload.status_code,
                    "_error_prefix": sanitize_response_text(upload.text),
                    "route": "chatgpt_backend_files",
                    "id": file_id,
                }
            finalize_url = f"{CHATGPT_BACKEND_BASE}/files/{file_id}/uploaded"
            final_payload: Dict[str, Any] = {}
            for _ in range(120):
                finalize = client.post(finalize_url, headers=headers, json={})
                final_payload = self._decode_json_response(finalize)
                if finalize.status_code >= 400:
                    return final_payload
                if final_payload.get("status") != "retry":
                    break
                time.sleep(0.25)
        download_url = final_payload.get("download_url")
        parsed_download = urlparse(download_url) if isinstance(download_url, str) else None
        record = {
            "id": file_id,
            "object": "oauth_compat.file",
            "route": "chatgpt_backend_files",
            "uri": f"sediment://{file_id}",
            "filename": final_payload.get("file_name") or path.name,
            "bytes": size,
            "mime_type": final_payload.get("mime_type"),
            "status": final_payload.get("status"),
            "download_url_present": bool(download_url),
            "download_url_host": parsed_download.netloc if parsed_download else None,
        }
        if include_download_url and isinstance(download_url, str):
            record["download_url"] = download_url
        return record

    def chatgpt_agent_identities_jwks_summary(self) -> Dict[str, Any]:
        payload = self.chatgpt_backend_get("/wham/agent-identities/jwks")
        keys = payload.get("keys") if isinstance(payload, dict) else None
        return {
            "object": "oauth_compat.agent_identities.jwks",
            "route": "chatgpt_backend_agent_identities_jwks",
            "_http_status": payload.get("_http_status") if isinstance(payload, dict) else None,
            "keys_count": len(keys) if isinstance(keys, list) else None,
        }

    def chatgpt_accounts_check_summary(self) -> Dict[str, Any]:
        payload = self.chatgpt_backend_get("/accounts/check/v4-2023-04-27")
        accounts = payload.get("accounts") if isinstance(payload, dict) else None
        ordering = payload.get("account_ordering") if isinstance(payload, dict) else None
        return {
            "object": "oauth_compat.accounts.check_summary",
            "route": "chatgpt_backend_accounts_check",
            "_http_status": payload.get("_http_status") if isinstance(payload, dict) else None,
            "accounts_count": len(accounts) if isinstance(accounts, dict) else None,
            "account_ordering_count": len(ordering) if isinstance(ordering, list) else None,
            "privacy_sensitive_values_redacted": True,
        }

    def chatgpt_me_summary(self) -> Dict[str, Any]:
        payload = self.chatgpt_backend_get("/me")
        return {
            "object": "oauth_compat.me_summary",
            "route": "chatgpt_backend_me",
            "_http_status": payload.get("_http_status") if isinstance(payload, dict) else None,
            "me_object": payload.get("object") if isinstance(payload, dict) else None,
            "has_id": bool(payload.get("id")) if isinstance(payload, dict) else None,
            "has_email": bool(payload.get("email")) if isinstance(payload, dict) else None,
            "privacy_sensitive_values_redacted": True,
        }

    def chatgpt_aura_site_status(self, site_url: str) -> Dict[str, Any]:
        payload = self.chatgpt_backend_get("/aura/site_status", params={
            "site_url": site_url,
            "url_request_source": "codex_browser_use",
        })
        feature_status = payload.get("feature_status") if isinstance(payload, dict) else None
        return {
            "object": "oauth_compat.aura.site_status",
            "route": "chatgpt_backend_aura_site_status",
            "_http_status": payload.get("_http_status") if isinstance(payload, dict) else None,
            "enabled": payload.get("enabled") if isinstance(payload, dict) else None,
            "feature_status_keys": sorted(feature_status.keys()) if isinstance(feature_status, dict) else [],
        }

    def chatgpt_curated_plugins_export(self, *, include_download_url: bool = False) -> Dict[str, Any]:
        payload = self.chatgpt_backend_get("/plugins/export/curated")
        download_url = payload.get("download_url") if isinstance(payload, dict) else None
        parsed = urlparse(download_url) if isinstance(download_url, str) else None
        record = {
            "object": "oauth_compat.plugins.curated_export",
            "route": "chatgpt_backend_plugins_export_curated",
            "_http_status": payload.get("_http_status") if isinstance(payload, dict) else None,
            "download_url_present": bool(download_url),
            "download_url_host": parsed.netloc if parsed else None,
        }
        if include_download_url and isinstance(download_url, str):
            record["download_url"] = download_url
        return record

    def chatgpt_plugins_list(self) -> Dict[str, Any]:
        return self.chatgpt_backend_get("/plugins/list")

    def chatgpt_plugins_featured(self) -> Dict[str, Any]:
        return self.chatgpt_backend_get("/plugins/featured", params={"platform": "codex"})

    def chatgpt_plugin_detail(self, plugin_id: str, *, include_download_urls: bool = False) -> Dict[str, Any]:
        params = {"includeDownloadUrls": "true"} if include_download_urls else None
        return self.chatgpt_backend_get(f"/ps/plugins/{plugin_id}", params=params)

    def chatgpt_plugin_skill_detail(self, plugin_id: str, skill_name: str) -> Dict[str, Any]:
        return self.chatgpt_backend_get(f"/ps/plugins/{plugin_id}/skills/{skill_name}")

    def chatgpt_workspace_plugins_shared(self) -> Dict[str, Any]:
        return self.chatgpt_backend_get("/ps/plugins/workspace/shared", params={"limit": 200})

    def chatgpt_connectors_directory_list(self, *, max_pages: int = 20) -> Dict[str, Any]:
        apps: list[Dict[str, Any]] = []
        token = None
        for _ in range(max_pages):
            params = {"external_logos": "true"}
            if token:
                params["token"] = token
            payload = self.chatgpt_backend_get("/connectors/directory/list", params=params)
            page_apps = payload.get("apps") if isinstance(payload, dict) else None
            if isinstance(page_apps, list):
                apps.extend(app for app in page_apps if isinstance(app, dict))
            token_value = payload.get("next_token") or payload.get("nextToken") if isinstance(payload, dict) else None
            token = token_value if isinstance(token_value, str) and token_value else None
            if not token:
                break
        return {
            "object": "oauth_compat.connectors.directory",
            "route": "chatgpt_backend_connectors_directory_list",
            "apps_count": len(apps),
            "apps": apps,
            "next_token_redacted": bool(token),
        }

    def chatgpt_connectors_directory_workspace(self) -> Dict[str, Any]:
        return self.chatgpt_backend_get("/connectors/directory/list_workspace", params={"external_logos": "true"})

    def chatgpt_usage(self) -> Dict[str, Any]:
        return self.chatgpt_backend_get("/wham/usage")

    def chatgpt_tasks_list(self, *, limit: int = 5) -> Dict[str, Any]:
        return self.chatgpt_backend_get("/wham/tasks/list", params={"limit": limit})

    def chatgpt_task_details(self, task_id: str) -> Dict[str, Any]:
        return self.chatgpt_backend_get(f"/wham/tasks/{task_id}")

    def chatgpt_task_sibling_turns(self, task_id: str, turn_id: str) -> Dict[str, Any]:
        return self.chatgpt_backend_get(f"/wham/tasks/{task_id}/turns/{turn_id}/sibling_turns")

    def chatgpt_environments(self) -> Dict[str, Any]:
        return self.chatgpt_backend_get("/wham/environments")

    def chatgpt_environments_by_repo(self, owner: str, repo: str, *, provider: str = "github") -> Dict[str, Any]:
        return self.chatgpt_backend_get(f"/wham/environments/by-repo/{provider}/{owner}/{repo}")

    def chatgpt_apps_mcp_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        headers = codex_headers(self.access_token)
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json, text/event-stream"
        body = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": method,
            "params": params or {},
        }
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.post(f"{CHATGPT_BACKEND_BASE}/wham/apps", headers=headers, json=body)
        return self._decode_json_response(response)

    def chatgpt_apps_tool_call(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.chatgpt_apps_mcp_request("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })

    def chatgpt_apps_tools_list(self) -> Dict[str, Any]:
        return self.chatgpt_apps_mcp_request("tools/list")

    def chatgpt_github_search_repositories(self, query: str, *, org: Optional[str] = None, per_page: int = 5) -> Dict[str, Any]:
        payload = self.chatgpt_apps_tool_call("github_search_repositories", {
            "query": query,
            "org": org,
            "per_page": per_page,
            "page": 1,
        })
        result = payload.get("result") if isinstance(payload, dict) else None
        repositories = []
        structured = result.get("structuredContent") if isinstance(result, dict) else None
        if isinstance(structured, dict) and isinstance(structured.get("repositories"), list):
            repositories = structured["repositories"]
        elif isinstance(result, dict) and isinstance(result.get("content"), list) and result["content"]:
            text = result["content"][0].get("text") if isinstance(result["content"][0], dict) else None
            if isinstance(text, str):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed.get("repositories"), list):
                        repositories = parsed["repositories"]
                except Exception:
                    repositories = []
        return {
            "object": "oauth_compat.github.repository_search",
            "route": "chatgpt_apps_mcp_tools_call",
            "_http_status": payload.get("_http_status") if isinstance(payload, dict) else None,
            "is_error": result.get("isError") if isinstance(result, dict) else None,
            "repositories_count": len(repositories),
            "repositories": repositories,
        }

    def chatgpt_backend_get(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        headers = codex_headers(self.access_token)
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(f"{CHATGPT_BACKEND_BASE}{path}", headers=headers, params=params)
        return self._decode_json_response(response)

    def realtime_client_secret(self, *, model: str = "gpt-realtime") -> str:
        response = self.official_post("/v1/realtime/client_secrets", json_body={
            "session": {"type": "realtime", "model": model},
        })
        value = response.get("value")
        if not isinstance(value, str) or not value:
            raise RuntimeError("Realtime client secret response did not contain value.")
        return value

    def realtime_transcription_session(self) -> Dict[str, Any]:
        return self.official_post("/v1/realtime/client_secrets", json_body={
            "session": {
                "type": "transcription",
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "transcription": {"model": "gpt-4o-mini-transcribe"},
                        "turn_detection": {"type": "server_vad"},
                    },
                },
            },
        })

    def realtime_webrtc_call_offer(
        self,
        offer_sdp: str,
        *,
        model: str = "gpt-realtime-1.5",
        instructions: str = "You are on a call.",
        voice: str = "marin",
    ) -> Dict[str, Any]:
        """Create a Realtime WebRTC call using a caller-supplied browser SDP offer."""
        boundary = "codex-realtime-call-boundary"
        session = json.dumps({
            "tool_choice": "auto",
            "type": "realtime",
            "model": model,
            "instructions": instructions,
            "output_modalities": ["audio"],
            "audio": {
                "input": {"format": {"type": "audio/pcm", "rate": 24000}},
                "output": {"format": {"type": "audio/pcm", "rate": 24000}, "voice": voice},
            },
        }, separators=(",", ":"))
        body = (
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"sdp\"\r\n"
            "Content-Type: application/sdp\r\n\r\n"
            f"{offer_sdp}\r\n"
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"session\"\r\n"
            "Content-Type: application/json\r\n\r\n"
            f"{session}\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.post("https://api.openai.com/v1/realtime/calls", headers=headers, content=body)
        return {
            "object": "oauth_compat.realtime.webrtc_call",
            "route": "official_realtime_calls",
            "_http_status": response.status_code,
            "location": response.headers.get("location"),
            "content_type": response.headers.get("content-type"),
            "answer_sdp": response.text if response.status_code < 400 else None,
            "_error_prefix": sanitize_response_text(response.text) if response.status_code >= 400 else None,
        }

    def realtime_say_to_pcm(self, text: str, output_path: Path | str) -> Path:
        return asyncio.run(self._realtime_say_to_pcm_async(text, Path(output_path)))

    async def _realtime_say_to_pcm_async(self, text: str, output_path: Path) -> Path:
        secret = self.realtime_client_secret()
        uri = "wss://api.openai.com/v1/realtime?model=gpt-realtime"
        audio_chunks: list[bytes] = []
        async with websockets.connect(
            uri,
            additional_headers={"Authorization": f"Bearer {secret}"},
            open_timeout=15,
            max_size=8 * 1024 * 1024,
        ) as ws:
            await ws.send(json.dumps({
                "type": "response.create",
                "response": {
                    "output_modalities": ["audio"],
                    "instructions": f"Say exactly: {text}",
                },
            }))
            deadline = time.time() + 35
            while time.time() < deadline:
                message = await asyncio.wait_for(ws.recv(), timeout=max(1.0, deadline - time.time()))
                event = json.loads(message)
                event_type = str(event.get("type", ""))
                if event_type == "error":
                    raise RuntimeError(sanitize_response_text(json.dumps(event.get("error", event)), limit=800))
                delta = event.get("delta")
                if isinstance(delta, str) and "audio" in event_type:
                    audio_chunks.append(base64.b64decode(delta))
                if event_type in {"response.done", "response.completed"}:
                    break
        output_path.write_bytes(b"".join(audio_chunks))
        return output_path

    def official_get(self, path: str, *, headers_extra: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        if headers_extra:
            headers.update(headers_extra)
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(f"https://api.openai.com{path}", headers=headers)
        return self._decode_json_response(response)

    def official_post(
        self,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        files: Any = None,
        headers_extra: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        if files is None:
            headers["Content-Type"] = "application/json"
        if headers_extra:
            headers.update(headers_extra)
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.post(f"https://api.openai.com{path}", headers=headers, json=json_body, files=files)
        return self._decode_json_response(response)

    def _decode_json_response(self, response: httpx.Response) -> Dict[str, Any]:
        try:
            payload = response.json()
        except Exception:
            payload = {"text": sanitize_response_text(response.text)}
        if not isinstance(payload, dict):
            payload = {"data": payload}
        payload["_http_status"] = response.status_code
        if response.status_code >= 400:
            payload["_error_prefix"] = sanitize_response_text(response.text)
        return payload


def main() -> int:
    oauth = OpenAIOAuthAccess()
    print(json.dumps({
        "runtime_source": oauth.source.name,
        "codex_base_url": CODEX_BASE_URL,
        "text_model": oauth.text_model,
        "image_host_model": oauth.image_host_model,
        "reasoning": CODEX_REASONING,
        "image_generation_model": "gpt-image-2",
        "image_generation_quality": IMAGE_GENERATION_QUALITY,
        "working_methods": [
            "codex_text",
            "codex_vision",
            "codex_generate_image",
            "official_transcribe_audio",
            "official_embedding",
            "realtime_client_secret",
            "realtime_transcription_session",
            "realtime_webrtc_call_offer",
            "realtime_say_to_pcm",
            "chatgpt_upload_file",
            "chatgpt_me_summary",
            "chatgpt_aura_site_status",
            "chatgpt_plugins_list",
            "chatgpt_plugins_featured",
            "chatgpt_plugin_detail",
            "chatgpt_plugin_skill_detail",
            "chatgpt_workspace_plugins_shared",
            "chatgpt_connectors_directory_list",
            "chatgpt_connectors_directory_workspace",
            "chatgpt_usage",
            "chatgpt_tasks_list",
            "chatgpt_task_details",
            "chatgpt_task_sibling_turns",
            "chatgpt_environments",
            "chatgpt_environments_by_repo",
            "chatgpt_apps_tools_list",
            "chatgpt_apps_tool_call",
            "chatgpt_github_search_repositories",
            "official_get",
            "official_post",
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
