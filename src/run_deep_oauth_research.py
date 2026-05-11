from __future__ import annotations

import dataclasses
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

import httpx

from codex_oauth import (
    CODEX_BASE_URL,
    choose_runtime_source,
    choose_text_model,
    codex_headers,
    decode_jwt_claims,
    fetch_codex_models,
    load_sources,
)
from run_oauth_matrix import sanitize_response_text


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ARTIFACTS = ROOT / "artifacts"
CHATGPT_BACKEND_BASE = "https://chatgpt.com/backend-api"
CHATGPT_CODEX_API_BASE = "https://chatgpt.com/api/codex"
LATEST_CODEX_SOURCE_HEAD = "4859d80ffeec76cc59c95fd274157c6b5560b4d2"


@dataclasses.dataclass
class ResearchResult:
    name: str
    status: str
    evidence: Dict[str, Any]
    error: Optional[str] = None


class DeepOAuthResearch:
    def __init__(self) -> None:
        self.sources = load_sources()
        self.runtime_source = choose_runtime_source(self.sources)
        self.access_token = self.runtime_source.access_token or ""
        self.model_ids = fetch_codex_models(self.access_token)
        self.text_model = choose_text_model(self.model_ids)
        self.results: list[ResearchResult] = []
        self.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def headers(self, *, json_content: bool = False) -> Dict[str, str]:
        headers = codex_headers(self.access_token)
        if json_content:
            headers["Content-Type"] = "application/json"
        return headers

    def record(self, result: ResearchResult) -> None:
        self.results.append(result)
        print(f"[{result.status}] {result.name}")

    def run_case(self, name: str, fn: Callable[[], Dict[str, Any]]) -> None:
        try:
            evidence = fn()
            status = evidence.pop("_status", "pass")
            self.record(ResearchResult(name=name, status=status, evidence=evidence))
        except Exception as exc:
            self.record(ResearchResult(
                name=name,
                status="fail",
                evidence={"exception_type": type(exc).__name__},
                error=sanitize_response_text(str(exc), limit=800),
            ))

    def classify(self, response: httpx.Response) -> str:
        if 200 <= response.status_code < 300:
            return "pass"
        if 300 <= response.status_code < 400:
            return "auth_accepted_request_invalid"
        text = response.text.lower()
        if response.status_code in (401, 403) or "unauthorized" in text or "forbidden" in text:
            return "expected_blocked"
        if response.status_code in (400, 404, 405, 415, 422):
            return "auth_accepted_request_invalid"
        return "fail"

    def evidence_for_response(self, response: httpx.Response, url: str) -> Dict[str, Any]:
        content_type = response.headers.get("content-type", "")
        return {
            "url": url,
            "http_status": response.status_code,
            "content_type": content_type[:120],
            "response_prefix": sanitize_response_text(response.text, limit=600),
            "_status": self.classify(response),
        }

    def realistic_webrtc_offer_sdp(self) -> str:
        fingerprint = ":".join(["AA"] * 32)
        lines = [
            "v=0",
            "o=- 4611731400430051336 2 IN IP4 127.0.0.1",
            "s=-",
            "t=0 0",
            "a=group:BUNDLE 0 1",
            "a=extmap-allow-mixed",
            "a=msid-semantic: WMS oauthprobe",
            "m=audio 9 UDP/TLS/RTP/SAVPF 111 63",
            "c=IN IP4 0.0.0.0",
            "a=rtcp:9 IN IP4 0.0.0.0",
            "a=ice-ufrag:abcd",
            "a=ice-pwd:abcdefghijklmnopqrstuv",
            "a=ice-options:trickle",
            f"a=fingerprint:sha-256 {fingerprint}",
            "a=setup:actpass",
            "a=mid:0",
            "a=sendrecv",
            "a=rtcp-mux",
            "a=rtcp-rsize",
            "a=rtpmap:111 opus/48000/2",
            "a=fmtp:111 minptime=10;useinbandfec=1",
            "a=rtpmap:63 red/48000/2",
            "a=fmtp:63 111/111",
            "a=ssrc:123456 cname:oauthprobe",
            "m=application 9 UDP/DTLS/SCTP webrtc-datachannel",
            "c=IN IP4 0.0.0.0",
            "a=ice-ufrag:abcd",
            "a=ice-pwd:abcdefghijklmnopqrstuv",
            "a=ice-options:trickle",
            f"a=fingerprint:sha-256 {fingerprint}",
            "a=setup:actpass",
            "a=mid:1",
            "a=sctp-port:5000",
        ]
        return "\r\n".join(lines) + "\r\n"

    def json_payload(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except Exception:
            text = response.text
            data_lines = []
            for line in text.splitlines():
                if line.startswith("data:"):
                    value = line.removeprefix("data:").strip()
                    if value and value != "[DONE]":
                        data_lines.append(value)
            for value in reversed(data_lines):
                try:
                    return json.loads(value)
                except Exception:
                    continue
            return None

    def add_json_summary(self, evidence: Dict[str, Any], payload: Any) -> Dict[str, Any]:
        if isinstance(payload, dict):
            evidence["top_level_keys"] = sorted(payload.keys())[:20]
            for key in ("plugins", "data", "tools", "resources", "prompts", "items", "models", "apps"):
                value = payload.get(key)
                if isinstance(value, list):
                    evidence[f"{key}_count"] = len(value)
                    names = []
                    for item in value[:5]:
                        if isinstance(item, dict):
                            name = item.get("name") or item.get("id") or item.get("slug") or item.get("title")
                            if isinstance(name, str):
                                names.append(name[:80])
                    if names:
                        evidence[f"first_{key}"] = names
            result = payload.get("result")
            if isinstance(result, dict):
                evidence["result_keys"] = sorted(result.keys())[:20]
                return self.add_json_summary(evidence, result)
        elif isinstance(payload, list):
            evidence["items_count"] = len(payload)
            names = []
            for item in payload[:5]:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("id") or item.get("slug") or item.get("title")
                    if isinstance(name, str):
                        names.append(name[:80])
            if names:
                evidence["first_items"] = names
        return evidence

    def classify_tool(self, name: str, description: str) -> str:
        lowered = f"{name} {description}".lower()
        mutation_markers = (
            "add_",
            "archive",
            "batch_modify",
            "bulk_label",
            "create",
            "delete",
            "dismiss",
            "enable",
            "forward",
            "install",
            "label",
            "lock",
            "mark_",
            "merge",
            "modify",
            "remove",
            "reply",
            "request_",
            "rerun",
            "resolve",
            "send",
            "trash",
            "uninstall",
            "unlock",
            "unresolve",
            "update",
        )
        if any(marker in lowered for marker in mutation_markers):
            return "mutation-capable"
        if "start the deep research" in lowered or "steer the deep research" in lowered:
            return "session-side-effect"
        return "read-like"

    def write_apps_tools_inventory(self, response_payload: Any, http_status: int) -> None:
        result = response_payload.get("result") if isinstance(response_payload, dict) else None
        tools = result.get("tools") if isinstance(result, dict) else None
        if not isinstance(tools, list):
            return
        inventory = []
        prefix_counts: Dict[str, int] = {}
        class_counts: Dict[str, int] = {}
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            name = tool.get("name")
            if not isinstance(name, str):
                continue
            description = tool.get("description")
            description = description if isinstance(description, str) else ""
            title = tool.get("title")
            title = title if isinstance(title, str) else name
            tool_class = self.classify_tool(name, description)
            prefix = name.split("_", 1)[0] if "_" in name else name.split(" ", 1)[0]
            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
            class_counts[tool_class] = class_counts.get(tool_class, 0) + 1
            inventory.append({
                "name": name,
                "title": title,
                "class": tool_class,
                "description_prefix": sanitize_response_text(description, limit=220),
            })
        inventory.sort(key=lambda item: (item["name"].split("_", 1)[0], item["name"]))
        payload = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "http_status": http_status,
            "tools_count": len(inventory),
            "prefix_counts": dict(sorted(prefix_counts.items())),
            "class_counts": dict(sorted(class_counts.items())),
            "note": "Metadata only. Personal-data tools and write-capable tools were not called.",
            "tools": inventory,
        }
        (REPORTS / "codex_apps_tools_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
        lines = [
            "# Codex Apps MCP Tools Inventory",
            "",
            f"- Generated: `{payload['generated_at']}`",
            f"- HTTP status: `{http_status}`",
            f"- Tools listed: `{len(inventory)}`",
            f"- Prefix counts: `{payload['prefix_counts']}`",
            f"- Class counts: `{payload['class_counts']}`",
            "- Source route: `POST https://chatgpt.com/backend-api/wham/apps` with `tools/list`",
            "- This is metadata only. Personal-data or write-capable tools were not called.",
            "",
            "| Heuristic class | Tool | Description prefix |",
            "|---|---|---|",
        ]
        for item in inventory:
            description = str(item["description_prefix"]).replace("|", "\\|")
            lines.append(f"| `{item['class']}` | `{item['name']}` | {description} |")
        (REPORTS / "codex_apps_tools_latest.md").write_text("\n".join(lines) + "\n")

    def first_global_plugin(self, *, limit: int = 20) -> Optional[Dict[str, Any]]:
        url = f"{CHATGPT_BACKEND_BASE}/ps/plugins/list"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"scope": "GLOBAL", "limit": limit})
        if response.status_code != 200:
            return None
        payload = self.json_payload(response)
        plugins = payload.get("plugins") if isinstance(payload, dict) else None
        if not isinstance(plugins, list):
            return None
        for plugin in plugins:
            if isinstance(plugin, dict) and isinstance(plugin.get("id"), str):
                return plugin
        return None

    def account_id(self) -> Optional[str]:
        claims = decode_jwt_claims(self.access_token)
        auth_claim = claims.get("https://api.openai.com/auth") or {}
        account_id = auth_claim.get("chatgpt_account_id")
        return account_id if isinstance(account_id, str) and account_id else None

    def test_chatgpt_backend_usage(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/wham/usage"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            payload = response.json()
            evidence["top_level_keys"] = sorted(payload.keys())[:20] if isinstance(payload, dict) else []
            evidence["has_rate_limit"] = "rate_limit" in payload if isinstance(payload, dict) else False
            evidence["has_credits"] = "credits" in payload if isinstance(payload, dict) else False
            evidence.pop("response_prefix", None)
        return evidence

    def test_codex_backend_models_direct(self) -> Dict[str, Any]:
        url = f"{CODEX_BASE_URL}/models"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"client_version": "1.0.0"})
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("first_models", None)
            evidence.pop("response_prefix", None)
        return evidence

    def test_codex_backend_responses_text_direct(self) -> Dict[str, Any]:
        url = f"{CODEX_BASE_URL}/responses"
        body = {
            "model": self.text_model,
            "store": False,
            "stream": True,
            "instructions": "Reply with exactly direct-codex-ok.",
            "input": [{
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Say direct-codex-ok."}],
            }],
        }
        with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
            response = client.post(url, headers=self.headers(json_content=True), json=body)
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            payload = self.json_payload(response)
            self.add_json_summary(evidence, payload)
            if isinstance(payload, dict):
                output = payload.get("output")
                evidence["output_count"] = len(output) if isinstance(output, list) else None
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_requirements(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/wham/config/requirements"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            payload = response.json()
            evidence["top_level_keys"] = sorted(payload.keys())[:20] if isinstance(payload, dict) else []
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_agent_identities_jwks(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/wham/agent-identities/jwks"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            payload = self.json_payload(response)
            keys = payload.get("keys") if isinstance(payload, dict) else None
            evidence["jwks_keys_count"] = len(keys) if isinstance(keys, list) else None
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_accounts_check_shape(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/accounts/check/v4-2023-04-27"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            payload = self.json_payload(response)
            accounts = payload.get("accounts") if isinstance(payload, dict) else None
            ordering = payload.get("account_ordering") if isinstance(payload, dict) else None
            evidence["top_level_keys"] = sorted(payload.keys())[:20] if isinstance(payload, dict) else []
            evidence["accounts_count"] = len(accounts) if isinstance(accounts, dict) else None
            evidence["account_ordering_count"] = len(ordering) if isinstance(ordering, list) else None
            evidence["privacy_sensitive_values_redacted"] = True
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_me_shape(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/me"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            payload = self.json_payload(response)
            evidence["top_level_keys"] = sorted(payload.keys())[:20] if isinstance(payload, dict) else []
            evidence["object"] = payload.get("object") if isinstance(payload, dict) else None
            evidence["has_id"] = bool(payload.get("id")) if isinstance(payload, dict) else None
            evidence["has_email"] = bool(payload.get("email")) if isinstance(payload, dict) else None
            evidence["privacy_sensitive_values_redacted"] = True
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_aura_site_status_example(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/aura/site_status"
        params = {
            "site_url": "https://example.com/",
            "url_request_source": "codex_browser_use",
        }
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params=params)
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            payload = self.json_payload(response)
            feature_status = payload.get("feature_status") if isinstance(payload, dict) else None
            evidence["top_level_keys"] = sorted(payload.keys())[:20] if isinstance(payload, dict) else []
            evidence["feature_status_keys"] = sorted(feature_status.keys())[:20] if isinstance(feature_status, dict) else []
            evidence["enabled"] = payload.get("enabled") if isinstance(payload, dict) else None
            evidence["site_url"] = "https://example.com/"
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_codex_api_usage_path(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/api/codex/usage"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        return self.evidence_for_response(response, url)

    def test_chatgpt_api_codex_usage_path(self) -> Dict[str, Any]:
        url = f"{CHATGPT_CODEX_API_BASE}/usage"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("first_items", None)
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_api_codex_models_path(self) -> Dict[str, Any]:
        url = f"{CHATGPT_CODEX_API_BASE}/models"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"client_version": "1.0.0"})
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("first_items", None)
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_api_codex_tasks_list(self) -> Dict[str, Any]:
        url = f"{CHATGPT_CODEX_API_BASE}/tasks/list"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"limit": 5})
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("first_items", None)
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_wham_tasks_list(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/wham/tasks/list"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"limit": 5})
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("first_items", None)
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_wham_task_detail_missing_id_shape(self) -> Dict[str, Any]:
        task_id = "task_000000000000000000000000"
        url = f"{CHATGPT_BACKEND_BASE}/wham/tasks/{task_id}"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        return self.evidence_for_response(response, url)

    def test_chatgpt_api_codex_task_detail_missing_id_shape(self) -> Dict[str, Any]:
        task_id = "task_000000000000000000000000"
        url = f"{CHATGPT_CODEX_API_BASE}/tasks/{task_id}"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        return self.evidence_for_response(response, url)

    def test_chatgpt_wham_task_sibling_turns_missing_id_shape(self) -> Dict[str, Any]:
        task_id = "task_000000000000000000000000"
        turn_id = "turn_000000000000000000000000"
        url = f"{CHATGPT_BACKEND_BASE}/wham/tasks/{task_id}/turns/{turn_id}/sibling_turns"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        return self.evidence_for_response(response, url)

    def test_chatgpt_api_codex_task_sibling_turns_missing_id_shape(self) -> Dict[str, Any]:
        task_id = "task_000000000000000000000000"
        turn_id = "turn_000000000000000000000000"
        url = f"{CHATGPT_CODEX_API_BASE}/tasks/{task_id}/turns/{turn_id}/sibling_turns"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        return self.evidence_for_response(response, url)

    def test_chatgpt_api_codex_environments(self) -> Dict[str, Any]:
        url = f"{CHATGPT_CODEX_API_BASE}/environments"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("first_items", None)
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_wham_environments(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/wham/environments"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("first_items", None)
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_api_codex_config_requirements(self) -> Dict[str, Any]:
        url = f"{CHATGPT_CODEX_API_BASE}/config/requirements"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_api_codex_apps_mcp_initialize(self) -> Dict[str, Any]:
        url = f"{CHATGPT_CODEX_API_BASE}/apps"
        body = {
            "jsonrpc": "2.0",
            "id": 21,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "chatgpt-oauth-bridge", "version": "0.1.0"},
            },
        }
        headers = self.headers(json_content=True)
        headers["Accept"] = "application/json, text/event-stream"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.post(url, headers=headers, json=body)
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_api_codex_responses_text(self) -> Dict[str, Any]:
        url = f"{CHATGPT_CODEX_API_BASE}/responses"
        body = {
            "model": self.text_model,
            "store": False,
            "instructions": "Reply with exactly api-codex-ok.",
            "input": [{
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Say api-codex-ok."}],
            }],
        }
        with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
            response = client.post(url, headers=self.headers(json_content=True), json=body)
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_file_upload(self) -> Dict[str, Any]:
        probe = ARTIFACTS / "codex_backend_upload_probe.txt"
        probe.write_text("OAuth Codex backend upload probe. No secrets.\n")
        create_url = f"{CHATGPT_BACKEND_BASE}/files"
        body = {
            "file_name": probe.name,
            "file_size": probe.stat().st_size,
            "use_case": "codex",
        }
        with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
            create = client.post(create_url, headers=self.headers(json_content=True), json=body)
            if create.status_code != 200:
                return self.evidence_for_response(create, create_url)
            payload = create.json()
            file_id = payload.get("file_id")
            upload_url = payload.get("upload_url")
            if not isinstance(file_id, str) or not isinstance(upload_url, str):
                return {
                    "url": create_url,
                    "http_status": create.status_code,
                    "response_prefix": sanitize_response_text(create.text, limit=600),
                    "reason": "missing file_id or upload_url",
                    "_status": "fail",
                }
            upload = client.put(
                upload_url,
                headers={
                    "x-ms-blob-type": "BlockBlob",
                    "Content-Length": str(probe.stat().st_size),
                },
                content=probe.read_bytes(),
            )
            if not (200 <= upload.status_code < 300):
                evidence = self.evidence_for_response(upload, "signed upload url")
                evidence["file_id_prefix"] = file_id[:12]
                return evidence
            finalize_url = f"{CHATGPT_BACKEND_BASE}/files/{file_id}/uploaded"
            finalize_payload = None
            for _ in range(20):
                finalize = client.post(finalize_url, headers=self.headers(json_content=True), json={})
                if finalize.status_code != 200:
                    evidence = self.evidence_for_response(finalize, finalize_url)
                    evidence["file_id_prefix"] = file_id[:12]
                    return evidence
                finalize_payload = finalize.json()
                if finalize_payload.get("status") != "retry":
                    break
                time.sleep(0.25)
            download_url = finalize_payload.get("download_url") if isinstance(finalize_payload, dict) else None
            parsed_download = urlparse(download_url) if isinstance(download_url, str) else None
            download_http_status = None
            download_sha256_prefix = None
            if isinstance(download_url, str) and download_url:
                download = client.get(download_url)
                download_http_status = download.status_code
                if download.status_code == 200:
                    download_sha256_prefix = hashlib.sha256(download.content).hexdigest()[:16]
        return {
            "url": create_url,
            "http_status": create.status_code,
            "file_id_prefix": file_id[:12],
            "uri": f"sediment://{file_id}",
            "upload_http_status": upload.status_code,
            "finalize_status": finalize_payload.get("status") if isinstance(finalize_payload, dict) else None,
            "download_probe_http_status": download_http_status,
            "download_probe_sha256_prefix": download_sha256_prefix,
            "download_url_present": bool(download_url),
            "download_url_host": parsed_download.netloc if parsed_download else None,
            "download_url_path_prefix": parsed_download.path[:80] if parsed_download else None,
            "file_name": finalize_payload.get("file_name") if isinstance(finalize_payload, dict) else None,
            "mime_type": finalize_payload.get("mime_type") if isinstance(finalize_payload, dict) else None,
            "file_size_bytes": probe.stat().st_size,
            "_status": "pass" if isinstance(finalize_payload, dict) and finalize_payload.get("status") == "success" else "fail",
        }

    def test_chatgpt_backend_curated_plugins_export(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/plugins/export/curated"
        with httpx.Client(timeout=httpx.Timeout(60.0), follow_redirects=False) as client:
            response = client.get(url, headers=self.headers())
            evidence = self.evidence_for_response(response, url)
            if response.status_code == 200:
                payload = self.json_payload(response)
                download_url = payload.get("download_url") if isinstance(payload, dict) else None
                parsed = urlparse(download_url) if isinstance(download_url, str) else None
                evidence["download_url_present"] = bool(download_url)
                evidence["download_url_host"] = parsed.netloc if parsed else None
                if isinstance(download_url, str) and download_url:
                    head = client.head(download_url)
                    evidence["download_probe_http_status"] = head.status_code
                    evidence["download_probe_content_type"] = head.headers.get("content-type", "")[:120]
                evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_ps_plugins_list_global(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/ps/plugins/list"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"scope": "GLOBAL", "limit": 20})
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_ps_plugins_installed_global(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/ps/plugins/installed"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"scope": "GLOBAL"})
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_ps_plugins_workspace_shared(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/ps/plugins/workspace/shared"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"limit": 200})
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_ps_plugins_first_global_detail(self) -> Dict[str, Any]:
        plugin = self.first_global_plugin()
        if not plugin:
            return {
                "url": f"{CHATGPT_BACKEND_BASE}/ps/plugins/<plugin-id>",
                "reason": "no global plugin id returned by list",
                "_status": "not_run_no_candidate",
            }
        plugin_id = plugin["id"]
        url = f"{CHATGPT_BACKEND_BASE}/ps/plugins/{plugin_id}"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        evidence = self.evidence_for_response(response, f"{CHATGPT_BACKEND_BASE}/ps/plugins/<plugin-id>")
        if response.status_code == 200:
            payload = self.json_payload(response)
            release = payload.get("release") if isinstance(payload, dict) else None
            skills = release.get("skills") if isinstance(release, dict) else None
            app_ids = release.get("app_ids") if isinstance(release, dict) else None
            evidence["plugin_id_prefix"] = plugin_id[:18]
            evidence["plugin_scope"] = payload.get("scope") if isinstance(payload, dict) else None
            evidence["plugin_name_present"] = bool(payload.get("name")) if isinstance(payload, dict) else None
            evidence["skills_count"] = len(skills) if isinstance(skills, list) else None
            evidence["app_ids_count"] = len(app_ids) if isinstance(app_ids, list) else None
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_ps_plugins_first_skill_detail(self) -> Dict[str, Any]:
        plugin = self.first_global_plugin()
        if not plugin:
            return {
                "url": f"{CHATGPT_BACKEND_BASE}/ps/plugins/<plugin-id>/skills/<skill-name>",
                "reason": "no global plugin id returned by list",
                "_status": "not_run_no_candidate",
            }
        plugin_id = plugin["id"]
        detail_url = f"{CHATGPT_BACKEND_BASE}/ps/plugins/{plugin_id}"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            detail = client.get(detail_url, headers=self.headers())
            if detail.status_code != 200:
                return self.evidence_for_response(detail, f"{CHATGPT_BACKEND_BASE}/ps/plugins/<plugin-id>")
            detail_payload = self.json_payload(detail)
            release = detail_payload.get("release") if isinstance(detail_payload, dict) else None
            skills = release.get("skills") if isinstance(release, dict) else None
            skill_name = None
            if isinstance(skills, list):
                for skill in skills:
                    if isinstance(skill, dict) and isinstance(skill.get("name"), str):
                        skill_name = skill["name"]
                        break
            if not skill_name:
                return {
                    "url": f"{CHATGPT_BACKEND_BASE}/ps/plugins/<plugin-id>/skills/<skill-name>",
                    "plugin_id_prefix": plugin_id[:18],
                    "reason": "first global plugin did not expose a skill",
                    "_status": "not_run_no_candidate",
                }
            skill_url = f"{CHATGPT_BACKEND_BASE}/ps/plugins/{plugin_id}/skills/{skill_name}"
            response = client.get(skill_url, headers=self.headers())
        evidence = self.evidence_for_response(response, f"{CHATGPT_BACKEND_BASE}/ps/plugins/<plugin-id>/skills/<skill-name>")
        if response.status_code == 200:
            payload = self.json_payload(response)
            contents = payload.get("skill_md_contents") if isinstance(payload, dict) else None
            evidence["plugin_id_prefix"] = plugin_id[:18]
            evidence["skill_name"] = skill_name[:80]
            evidence["skill_contents_present"] = isinstance(contents, str)
            evidence["skill_contents_chars"] = len(contents) if isinstance(contents, str) else None
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_plugins_list_legacy(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/plugins/list"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_plugins_featured(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/plugins/featured"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"platform": "codex"})
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_plugins_featured_chat(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/plugins/featured"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"platform": "chat"})
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_connectors_directory_list(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/connectors/directory/list"
        total_apps = 0
        pages_fetched = 0
        first_apps: list[str] = []
        token = None
        last_status = None
        last_content_type = None
        with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
            for _ in range(20):
                params = {"external_logos": "true"}
                if token:
                    params["token"] = token
                response = client.get(url, headers=self.headers(), params=params)
                last_status = response.status_code
                last_content_type = response.headers.get("content-type", "")
                if response.status_code != 200:
                    evidence = self.evidence_for_response(response, url)
                    evidence["pages_fetched"] = pages_fetched
                    evidence["apps_count"] = total_apps
                    return evidence
                payload = self.json_payload(response)
                apps = payload.get("apps") if isinstance(payload, dict) else None
                if isinstance(apps, list):
                    total_apps += len(apps)
                    for app in apps[: max(0, 5 - len(first_apps))]:
                        if isinstance(app, dict):
                            name = app.get("name") or app.get("id")
                            if isinstance(name, str):
                                first_apps.append(name[:80])
                pages_fetched += 1
                next_token = None
                if isinstance(payload, dict):
                    next_token = payload.get("next_token") or payload.get("nextToken")
                token = next_token if isinstance(next_token, str) and next_token else None
                if not token:
                    break
        evidence = {
            "url": url,
            "http_status": last_status,
            "content_type": (last_content_type or "")[:120],
            "apps_count": total_apps,
            "pages_fetched": pages_fetched,
            "first_apps": first_apps,
            "next_token_redacted": bool(token),
            "_status": "pass" if last_status == 200 else "fail",
        }
        return evidence

    def test_chatgpt_backend_connectors_directory_workspace(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/connectors/directory/list_workspace"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"external_logos": "true"})
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_environments_by_repo_openai_codex(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/wham/environments/by-repo/github/openai/codex"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers())
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence["repo_probe"] = "github/openai/codex"
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_workspace_plugin_shares_created(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/ps/plugins/workspace/created"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"limit": 200})
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_ps_plugins_list_workspace(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/ps/plugins/list"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"scope": "WORKSPACE", "limit": 200})
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_ps_plugins_installed_workspace(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/ps/plugins/installed"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(
                url,
                headers=self.headers(),
                params={"scope": "WORKSPACE", "includeDownloadUrls": "true"},
            )
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_account_settings(self) -> Dict[str, Any]:
        account_id = self.account_id()
        if not account_id:
            return {
                "url": f"{CHATGPT_BACKEND_BASE}/accounts/<account-id>/settings",
                "reason": "no account id claim",
                "_status": "expected_blocked",
            }
        actual_url = f"{CHATGPT_BACKEND_BASE}/accounts/{account_id}/settings"
        report_url = f"{CHATGPT_BACKEND_BASE}/accounts/<account-id>/settings"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(actual_url, headers=self.headers())
        evidence = self.evidence_for_response(response, report_url)
        if response.status_code == 200:
            payload = self.json_payload(response)
            self.add_json_summary(evidence, payload)
            if isinstance(payload, dict) and isinstance(payload.get("beta_settings"), dict):
                evidence["beta_settings_count"] = len(payload["beta_settings"])
                evidence["beta_settings_keys_sample"] = sorted(payload["beta_settings"].keys())[:10]
            evidence.pop("response_prefix", None)
        return evidence

    def wham_apps_request(self, body: Dict[str, Any]) -> httpx.Response:
        url = f"{CHATGPT_BACKEND_BASE}/wham/apps"
        headers = self.headers(json_content=True)
        headers["Accept"] = "application/json, text/event-stream"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            return client.post(url, headers=headers, json=body)

    def test_chatgpt_apps_mcp_tools_list(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/wham/apps"
        init = self.wham_apps_request({
            "jsonrpc": "2.0",
            "id": 11,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "chatgpt-oauth-bridge", "version": "0.1.0"},
            },
        })
        response = self.wham_apps_request({
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/list",
            "params": {},
        })
        evidence = self.evidence_for_response(response, url)
        evidence["initialize_http_status"] = init.status_code
        if response.status_code == 200:
            payload = self.json_payload(response)
            self.add_json_summary(evidence, payload)
            self.write_apps_tools_inventory(payload, response.status_code)
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_apps_mcp_resources_list(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/wham/apps"
        response = self.wham_apps_request({
            "jsonrpc": "2.0",
            "id": 13,
            "method": "resources/list",
            "params": {},
        })
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_apps_mcp_prompts_list(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/wham/apps"
        response = self.wham_apps_request({
            "jsonrpc": "2.0",
            "id": 14,
            "method": "prompts/list",
            "params": {},
        })
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_apps_mcp_github_search_repositories_call(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/wham/apps"
        response = self.wham_apps_request({
            "jsonrpc": "2.0",
            "id": 15,
            "method": "tools/call",
            "params": {
                "name": "github_search_repositories",
                "arguments": {
                    "query": "codex",
                    "org": "openai",
                    "per_page": 3,
                    "page": 1,
                },
            },
        })
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            payload = self.json_payload(response)
            result = payload.get("result") if isinstance(payload, dict) else None
            evidence["result_keys"] = sorted(result.keys())[:20] if isinstance(result, dict) else []
            evidence["tool_call_is_error"] = result.get("isError") if isinstance(result, dict) else None
            repositories_count = None
            first_public_repositories = []
            structured = result.get("structuredContent") if isinstance(result, dict) else None
            if isinstance(structured, dict):
                repos = structured.get("repositories")
                if isinstance(repos, list):
                    repositories_count = len(repos)
                    for repo in repos[:3]:
                        if isinstance(repo, dict):
                            name = repo.get("repository_full_name") or repo.get("full_name") or repo.get("name")
                            if isinstance(name, str):
                                first_public_repositories.append(name)
            if repositories_count is None and isinstance(result, dict):
                content = result.get("content")
                if isinstance(content, list) and content:
                    text = content[0].get("text") if isinstance(content[0], dict) else None
                    if isinstance(text, str):
                        try:
                            parsed = json.loads(text)
                            repos = parsed.get("repositories")
                            if isinstance(repos, list):
                                repositories_count = len(repos)
                                for repo in repos[:3]:
                                    if isinstance(repo, dict):
                                        name = repo.get("repository_full_name") or repo.get("full_name") or repo.get("name")
                                        if isinstance(name, str):
                                            first_public_repositories.append(name)
                        except Exception:
                            pass
            evidence["repositories_count"] = repositories_count
            if first_public_repositories:
                evidence["first_public_repositories"] = first_public_repositories
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_backend_github_repositories_search_route_shape(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/wham/github/repositories/search"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(url, headers=self.headers(), params={"query": "openai/codex"})
        return self.evidence_for_response(response, url)

    def test_codex_backend_compact(self) -> Dict[str, Any]:
        url = f"{CODEX_BASE_URL}/responses/compact"
        body = {
            "model": self.text_model,
            "instructions": "Compact the input into one short item.",
            "input": [{
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "OAuth compact probe: preserve the word compact-ok."}],
            }],
            "tools": [],
            "parallel_tool_calls": True,
        }
        with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
            response = client.post(url, headers=self.headers(json_content=True), json=body)
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            payload = response.json()
            output = payload.get("output") if isinstance(payload, dict) else None
            evidence["output_count"] = len(output) if isinstance(output, list) else None
            evidence.pop("response_prefix", None)
        return evidence

    def test_codex_backend_memories_trace_summarize(self) -> Dict[str, Any]:
        url = f"{CODEX_BASE_URL}/memories/trace_summarize"
        body = {
            "model": self.text_model,
            "traces": [{
                "id": "oauth-memory-probe-1",
                "metadata": {"source_path": "chatgpt-oauth-bridge"},
                "items": [{
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "The user wants OAuth-only OpenAI feature coverage."}],
                }],
            }],
        }
        with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
            response = client.post(url, headers=self.headers(json_content=True), json=body)
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            payload = response.json()
            output = payload.get("output") if isinstance(payload, dict) else None
            evidence["output_count"] = len(output) if isinstance(output, list) else None
            evidence["first_keys"] = sorted(output[0].keys()) if isinstance(output, list) and output and isinstance(output[0], dict) else []
            evidence.pop("response_prefix", None)
        return evidence

    def test_codex_backend_v1_memories_trace_summarize(self) -> Dict[str, Any]:
        url = f"{CODEX_BASE_URL}/v1/memories/trace_summarize"
        body = {
            "model": self.text_model,
            "traces": [{
                "id": "oauth-memory-probe-2",
                "items": [{
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "OAuth memory v1 probe."}],
                }],
            }],
        }
        with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
            response = client.post(url, headers=self.headers(json_content=True), json=body)
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            self.add_json_summary(evidence, self.json_payload(response))
            evidence.pop("response_prefix", None)
        return evidence

    def test_codex_backend_realtime_call_json_shape(self) -> Dict[str, Any]:
        url = f"{CODEX_BASE_URL}/realtime/calls"
        body = {
            "sdp": "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=oauth-probe\r\nt=0 0\r\n",
            "session": {
                "type": "realtime",
                "model": "gpt-realtime",
                "output_modalities": ["audio"],
            },
        }
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.post(url, headers=self.headers(json_content=True), json=body)
        return self.evidence_for_response(response, url)

    def test_openai_realtime_calls_application_sdp_shape(self) -> Dict[str, Any]:
        url = "https://api.openai.com/v1/realtime/calls"
        sdp = "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=oauth-sdp-probe\r\nt=0 0\r\n"
        headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/sdp"}
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.post(url, headers=headers, content=sdp)
        return self.evidence_for_response(response, url)

    def test_openai_realtime_calls_multipart_shape(self) -> Dict[str, Any]:
        url = "https://api.openai.com/v1/realtime/calls"
        boundary = "codex-realtime-call-boundary"
        sdp = "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=oauth-multipart-probe\r\nt=0 0\r\n"
        session = json.dumps({
            "type": "realtime",
            "model": "gpt-realtime",
            "audio": {"output": {"voice": "cove"}},
        }, separators=(",", ":"))
        body = (
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"sdp\"\r\n"
            "Content-Type: application/sdp\r\n\r\n"
            f"{sdp}\r\n"
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
            response = client.post(url, headers=headers, content=body)
        return self.evidence_for_response(response, url)

    def test_openai_realtime_calls_multipart_valid_sdp(self) -> Dict[str, Any]:
        url = "https://api.openai.com/v1/realtime/calls"
        boundary = "codex-realtime-call-boundary"
        sdp = self.realistic_webrtc_offer_sdp()
        session = json.dumps({
            "tool_choice": "auto",
            "type": "realtime",
            "model": "gpt-realtime-1.5",
            "instructions": "oauth legal probe",
            "output_modalities": ["audio"],
            "audio": {
                "input": {"format": {"type": "audio/pcm", "rate": 24000}},
                "output": {"format": {"type": "audio/pcm", "rate": 24000}, "voice": "marin"},
            },
        }, separators=(",", ":"))
        body = (
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"sdp\"\r\n"
            "Content-Type: application/sdp\r\n\r\n"
            f"{sdp}\r\n"
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
            response = client.post(url, headers=headers, content=body)
        evidence = self.evidence_for_response(response, url)
        if 200 <= response.status_code < 300:
            location = response.headers.get("location") or ""
            parsed_location = urlparse(location)
            path_parts = [part for part in parsed_location.path.split("/") if part]
            if path_parts:
                path_parts[-1] = "<call-id>"
            evidence["location_header_present"] = bool(location)
            evidence["location_path_shape"] = "/" + "/".join(path_parts) if path_parts else None
            evidence["answer_sdp_present"] = response.text.startswith("v=0")
            evidence["answer_sdp_line_count"] = len(response.text.splitlines())
            evidence["answer_sdp_sha256_prefix"] = hashlib.sha256(response.content).hexdigest()[:16]
            evidence.pop("response_prefix", None)
        return evidence

    def test_chatgpt_apps_mcp_initialize_probe(self) -> Dict[str, Any]:
        url = f"{CHATGPT_BACKEND_BASE}/wham/apps"
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "chatgpt-oauth-bridge", "version": "0.1.0"},
            },
        }
        headers = self.headers(json_content=True)
        headers["Accept"] = "application/json, text/event-stream"
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.post(url, headers=headers, json=body)
        evidence = self.evidence_for_response(response, url)
        if response.status_code == 200:
            evidence["response_prefix"] = sanitize_response_text(response.text, limit=1000)
        return evidence

    def test_source_route_chatgpt_task_create_not_run(self) -> Dict[str, Any]:
        return {
            "source_route": "POST /backend-api/wham/tasks",
            "reason": "creates a real Codex cloud task; source-backed but not auto-probed",
            "source_file": "openai/codex codex-rs/backend-client/src/client.rs",
            "_status": "not_run_side_effect",
        }

    def test_source_route_chatgpt_remote_control_not_run(self) -> Dict[str, Any]:
        return {
            "source_route": "POST /backend-api/wham/remote/control/server/enroll; "
                            "WSS /backend-api/wham/remote/control/server",
            "reason": "enrolls and controls an app-server environment; source-backed but not auto-probed",
            "source_file": "openai/codex codex-rs/app-server-transport/src/transport/remote_control",
            "_status": "not_run_side_effect",
        }

    def test_source_route_chatgpt_workspace_plugin_share_not_run(self) -> Dict[str, Any]:
        return {
            "source_route": "POST /backend-api/public/plugins/workspace/upload-url; "
                            "POST /backend-api/public/plugins/workspace; "
                            "POST /backend-api/public/plugins/workspace/{remote_plugin_id}; "
                            "PUT /backend-api/ps/plugins/{remote_plugin_id}/shares; "
                            "DELETE /backend-api/public/plugins/workspace/{remote_plugin_id}",
            "reason": "can publish/update/delete a workspace plugin share; source-backed but not auto-probed",
            "source_file": "openai/codex codex-rs/core-plugins/src/remote/share.rs",
            "_status": "not_run_side_effect",
        }

    def test_source_route_chatgpt_plugin_install_not_run(self) -> Dict[str, Any]:
        return {
            "source_route": "POST /backend-api/ps/plugins/{plugin_id}/install; "
                            "POST /backend-api/plugins/{plugin_id}/uninstall",
            "reason": "changes installed plugin state; source-backed but not auto-probed",
            "source_file": "openai/codex codex-rs/core-plugins/src/remote.rs",
            "_status": "not_run_side_effect",
        }

    def test_source_route_codex_add_credits_nudge_not_run(self) -> Dict[str, Any]:
        return {
            "source_route": "POST /backend-api/wham/accounts/send_add_credits_nudge_email; "
                            "POST /api/codex/accounts/send_add_credits_nudge_email",
            "reason": "sends a real account email/nudge; source-backed but not auto-probed",
            "source_file": "openai/codex codex-rs/backend-client/src/client.rs",
            "_status": "not_run_side_effect",
        }

    def test_source_route_codex_analytics_events_not_run(self) -> Dict[str, Any]:
        return {
            "source_route": "POST /backend-api/codex/analytics-events/events",
            "reason": "telemetry write path, not an app feature workaround",
            "source_file": "openai/codex codex-rs/analytics/src/client.rs",
            "_status": "not_run_side_effect",
        }

    def test_source_route_codex_responses_api_proxy_not_oauth(self) -> Dict[str, Any]:
        return {
            "source_route": "POST /v1/responses via codex-responses-api-proxy",
            "reason": "official Codex proxy is source-backed, but it reads OPENAI_API_KEY from stdin and is not an OAuth-only path",
            "source_file": "openai/codex codex-rs/responses-api-proxy/README.md",
            "_status": "not_oauth_api_key_proxy",
        }

    def write_report(self) -> None:
        REPORTS.mkdir(exist_ok=True)
        finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        payload = {
            "started_at": self.started_at,
            "finished_at": finished_at,
            "runtime_source": self.runtime_source.name,
            "text_model": self.text_model,
            "openai_codex_source_head": LATEST_CODEX_SOURCE_HEAD,
            "results": [dataclasses.asdict(result) for result in self.results],
        }
        (REPORTS / "deep_oauth_research_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
        lines = [
            "# Deep OAuth Research Report",
            "",
            f"- Started: `{self.started_at}`",
            f"- Finished: `{finished_at}`",
            f"- Runtime source: `{self.runtime_source.name}`",
            f"- Text model: `{self.text_model}`",
            f"- openai/codex source HEAD checked this run: `{LATEST_CODEX_SOURCE_HEAD}`",
            "",
            "| Status | Probe | Evidence |",
            "|---|---|---|",
        ]
        keys = (
            "http_status",
            "url",
            "file_id_prefix",
            "uri",
            "upload_http_status",
            "finalize_status",
            "download_url_present",
            "download_url_host",
            "download_probe_http_status",
            "download_probe_sha256_prefix",
            "output_count",
            "plugins_count",
            "data_count",
            "tools_count",
            "resources_count",
            "prompts_count",
            "items_count",
            "models_count",
            "apps_count",
            "pages_fetched",
            "jwks_keys_count",
            "accounts_count",
            "account_ordering_count",
            "object",
            "has_id",
            "has_email",
            "enabled",
            "feature_status_keys",
            "repositories_count",
            "initialize_http_status",
            "beta_settings_count",
            "has_rate_limit",
            "has_credits",
            "plugin_id_prefix",
            "plugin_scope",
            "plugin_name_present",
            "skills_count",
            "app_ids_count",
            "skill_name",
            "skill_contents_present",
            "skill_contents_chars",
            "answer_sdp_present",
            "answer_sdp_line_count",
            "answer_sdp_sha256_prefix",
            "location_header_present",
            "location_path_shape",
            "source_route",
            "reason",
            "source_file",
        )
        for result in self.results:
            bits = [f"{key}={result.evidence[key]}" for key in keys if result.evidence.get(key) is not None]
            if result.error:
                bits.append(f"error={result.error[:180]}")
            lines.append(f"| `{result.status}` | `{result.name}` | {'; '.join(bits)[:700]} |")
        lines.append("")
        lines.append("No access tokens, refresh tokens, Authorization headers, signed upload URLs, or raw SAS query strings are stored in this report.")
        (REPORTS / "deep_oauth_research_latest.md").write_text("\n".join(lines) + "\n")

    def run(self) -> int:
        REPORTS.mkdir(exist_ok=True)
        ARTIFACTS.mkdir(exist_ok=True)
        self.run_case("chatgpt_backend_usage", self.test_chatgpt_backend_usage)
        self.run_case("codex_backend_models_direct", self.test_codex_backend_models_direct)
        self.run_case("codex_backend_responses_text_direct", self.test_codex_backend_responses_text_direct)
        self.run_case("chatgpt_backend_requirements", self.test_chatgpt_backend_requirements)
        self.run_case("chatgpt_backend_agent_identities_jwks", self.test_chatgpt_backend_agent_identities_jwks)
        self.run_case("chatgpt_backend_accounts_check_shape", self.test_chatgpt_backend_accounts_check_shape)
        self.run_case("chatgpt_backend_me_shape", self.test_chatgpt_backend_me_shape)
        self.run_case("chatgpt_backend_aura_site_status_example", self.test_chatgpt_backend_aura_site_status_example)
        self.run_case("chatgpt_codex_api_usage_path", self.test_chatgpt_codex_api_usage_path)
        self.run_case("chatgpt_api_codex_usage_path", self.test_chatgpt_api_codex_usage_path)
        self.run_case("chatgpt_api_codex_models_path", self.test_chatgpt_api_codex_models_path)
        self.run_case("chatgpt_api_codex_tasks_list", self.test_chatgpt_api_codex_tasks_list)
        self.run_case("chatgpt_wham_tasks_list", self.test_chatgpt_wham_tasks_list)
        self.run_case("chatgpt_wham_task_detail_missing_id_shape", self.test_chatgpt_wham_task_detail_missing_id_shape)
        self.run_case("chatgpt_api_codex_task_detail_missing_id_shape", self.test_chatgpt_api_codex_task_detail_missing_id_shape)
        self.run_case("chatgpt_wham_task_sibling_turns_missing_id_shape", self.test_chatgpt_wham_task_sibling_turns_missing_id_shape)
        self.run_case("chatgpt_api_codex_task_sibling_turns_missing_id_shape", self.test_chatgpt_api_codex_task_sibling_turns_missing_id_shape)
        self.run_case("chatgpt_api_codex_environments", self.test_chatgpt_api_codex_environments)
        self.run_case("chatgpt_wham_environments", self.test_chatgpt_wham_environments)
        self.run_case("chatgpt_api_codex_config_requirements", self.test_chatgpt_api_codex_config_requirements)
        self.run_case("chatgpt_api_codex_apps_mcp_initialize", self.test_chatgpt_api_codex_apps_mcp_initialize)
        self.run_case("chatgpt_api_codex_responses_text", self.test_chatgpt_api_codex_responses_text)
        self.run_case("chatgpt_backend_file_upload", self.test_chatgpt_backend_file_upload)
        self.run_case("chatgpt_backend_curated_plugins_export", self.test_chatgpt_backend_curated_plugins_export)
        self.run_case("chatgpt_backend_ps_plugins_list_global", self.test_chatgpt_backend_ps_plugins_list_global)
        self.run_case("chatgpt_backend_ps_plugins_installed_global", self.test_chatgpt_backend_ps_plugins_installed_global)
        self.run_case("chatgpt_backend_ps_plugins_workspace_shared", self.test_chatgpt_backend_ps_plugins_workspace_shared)
        self.run_case("chatgpt_backend_ps_plugins_first_global_detail", self.test_chatgpt_backend_ps_plugins_first_global_detail)
        self.run_case("chatgpt_backend_ps_plugins_first_skill_detail", self.test_chatgpt_backend_ps_plugins_first_skill_detail)
        self.run_case("chatgpt_backend_plugins_list_legacy", self.test_chatgpt_backend_plugins_list_legacy)
        self.run_case("chatgpt_backend_plugins_featured", self.test_chatgpt_backend_plugins_featured)
        self.run_case("chatgpt_backend_plugins_featured_chat", self.test_chatgpt_backend_plugins_featured_chat)
        self.run_case("chatgpt_backend_connectors_directory_list", self.test_chatgpt_backend_connectors_directory_list)
        self.run_case("chatgpt_backend_connectors_directory_workspace", self.test_chatgpt_backend_connectors_directory_workspace)
        self.run_case("chatgpt_backend_environments_by_repo_openai_codex", self.test_chatgpt_backend_environments_by_repo_openai_codex)
        self.run_case("chatgpt_backend_workspace_plugin_shares_created", self.test_chatgpt_backend_workspace_plugin_shares_created)
        self.run_case("chatgpt_backend_ps_plugins_list_workspace", self.test_chatgpt_backend_ps_plugins_list_workspace)
        self.run_case("chatgpt_backend_ps_plugins_installed_workspace", self.test_chatgpt_backend_ps_plugins_installed_workspace)
        self.run_case("chatgpt_backend_account_settings", self.test_chatgpt_backend_account_settings)
        self.run_case("codex_backend_compact", self.test_codex_backend_compact)
        self.run_case("codex_backend_memories_trace_summarize", self.test_codex_backend_memories_trace_summarize)
        self.run_case("codex_backend_v1_memories_trace_summarize", self.test_codex_backend_v1_memories_trace_summarize)
        self.run_case("codex_backend_realtime_call_json_shape", self.test_codex_backend_realtime_call_json_shape)
        self.run_case("openai_realtime_calls_application_sdp_shape", self.test_openai_realtime_calls_application_sdp_shape)
        self.run_case("openai_realtime_calls_multipart_shape", self.test_openai_realtime_calls_multipart_shape)
        self.run_case("openai_realtime_calls_multipart_valid_sdp", self.test_openai_realtime_calls_multipart_valid_sdp)
        self.run_case("chatgpt_apps_mcp_initialize_probe", self.test_chatgpt_apps_mcp_initialize_probe)
        self.run_case("chatgpt_apps_mcp_tools_list", self.test_chatgpt_apps_mcp_tools_list)
        self.run_case("chatgpt_apps_mcp_resources_list", self.test_chatgpt_apps_mcp_resources_list)
        self.run_case("chatgpt_apps_mcp_prompts_list", self.test_chatgpt_apps_mcp_prompts_list)
        self.run_case("chatgpt_apps_mcp_github_search_repositories_call", self.test_chatgpt_apps_mcp_github_search_repositories_call)
        self.run_case("chatgpt_backend_github_repositories_search_route_shape", self.test_chatgpt_backend_github_repositories_search_route_shape)
        self.run_case("source_route_chatgpt_task_create_not_run", self.test_source_route_chatgpt_task_create_not_run)
        self.run_case("source_route_chatgpt_remote_control_not_run", self.test_source_route_chatgpt_remote_control_not_run)
        self.run_case("source_route_chatgpt_workspace_plugin_share_not_run", self.test_source_route_chatgpt_workspace_plugin_share_not_run)
        self.run_case("source_route_chatgpt_plugin_install_not_run", self.test_source_route_chatgpt_plugin_install_not_run)
        self.run_case("source_route_codex_add_credits_nudge_not_run", self.test_source_route_codex_add_credits_nudge_not_run)
        self.run_case("source_route_codex_analytics_events_not_run", self.test_source_route_codex_analytics_events_not_run)
        self.run_case("source_route_codex_responses_api_proxy_not_oauth", self.test_source_route_codex_responses_api_proxy_not_oauth)
        self.write_report()
        return 0


def main() -> int:
    return DeepOAuthResearch().run()


if __name__ == "__main__":
    raise SystemExit(main())
