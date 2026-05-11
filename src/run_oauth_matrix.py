from __future__ import annotations

import argparse
import asyncio
import base64
import dataclasses
import hashlib
import json
import os
import re
import sys
import time
import traceback
import wave
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, Optional

import httpx
import websockets
from PIL import Image

from codex_oauth import (
    CODEX_BASE_URL,
    choose_image_host_model,
    choose_runtime_source,
    choose_text_model,
    codex_headers,
    codex_openai_client,
    fetch_codex_models,
    load_sources,
    redacted_headers_for_report,
    token_metadata,
)


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ARTIFACTS = ROOT / "artifacts"


def sanitize_response_text(text: str, limit: int = 400) -> str:
    """Keep reports useful without storing bearer/API/ephemeral secrets."""
    redacted = re.sub(r"ek_[A-Za-z0-9_-]+", "ek_<redacted>", text)
    redacted = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-<redacted>", redacted)
    redacted = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer <redacted>", redacted)
    return redacted[:limit]


@dataclasses.dataclass
class TestResult:
    name: str
    category: str
    status: str
    evidence: Dict[str, Any]
    error: Optional[str] = None


class Matrix:
    def __init__(self, *, include_images: bool, include_official_negative: bool):
        self.include_images = include_images
        self.include_official_negative = include_official_negative
        self.results: list[TestResult] = []
        self.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.sources = load_sources()
        self.runtime_source = choose_runtime_source(self.sources)
        self.access_token = self.runtime_source.access_token or ""
        self.model_ids: list[str] = []
        self.text_model = ""
        self.image_host_model = ""

    def record(self, result: TestResult) -> None:
        self.results.append(result)
        print(f"[{result.status}] {result.name}")

    def run_case(
        self,
        name: str,
        category: str,
        fn: Callable[[], Dict[str, Any]],
        *,
        expected_blocked: bool = False,
    ) -> None:
        try:
            evidence = fn()
            status = evidence.pop("_status", "pass")
            self.record(TestResult(name=name, category=category, status=status, evidence=evidence))
        except Exception as exc:
            status = "expected_blocked" if expected_blocked else "fail"
            self.record(TestResult(
                name=name,
                category=category,
                status=status,
                evidence={"exception_type": type(exc).__name__},
                error=str(exc),
            ))

    def test_token_inventory(self) -> Dict[str, Any]:
        return {
            "runtime_source": self.runtime_source.name,
            "sources": [token_metadata(source) for source in self.sources],
        }

    def test_no_platform_api_key_env(self) -> Dict[str, Any]:
        import os

        blocked = {
            "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
            "OPENAI_ADMIN_KEY": bool(os.environ.get("OPENAI_ADMIN_KEY")),
        }
        return {
            "uses_openai_api_key": any(blocked.values()),
            "env_presence": blocked,
            "_status": "fail" if any(blocked.values()) else "pass",
        }

    def test_codex_models(self) -> Dict[str, Any]:
        self.model_ids = fetch_codex_models(self.access_token)
        self.text_model = choose_text_model(self.model_ids)
        self.image_host_model = choose_image_host_model(self.model_ids)
        return {
            "base_url": CODEX_BASE_URL,
            "model_count": len(self.model_ids),
            "models": self.model_ids,
            "selected_text_model": self.text_model,
            "selected_image_host_model": self.image_host_model,
            "request_headers": redacted_headers_for_report(codex_headers(self.access_token)),
        }

    def test_text_response(self) -> Dict[str, Any]:
        text, output_types = self._stream_text_response(
            model=self.text_model or "gpt-5.4-mini",
            instructions="Follow the user's instruction exactly.",
            input_payload=[{
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Reply with exactly: oauth text ok"}],
            }],
        )
        return {
            "model": self.text_model,
            "output_text": text[:200],
            "output_types": output_types,
            "_status": "pass" if "oauth text ok" in text.lower() else "fail",
        }

    def _response_text_and_types(self, response: Any) -> tuple[str, list[str]]:
        output_text = getattr(response, "output_text", "") or ""
        output_types: list[str] = []
        chunks: list[str] = []
        for item in getattr(response, "output", []) or []:
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

    def _stream_text_response(self, *, model: str, instructions: str, input_payload: list[dict[str, Any]]) -> tuple[str, list[str]]:
        client = codex_openai_client(self.access_token)
        final = None
        collected_output_items: list[Any] = []
        collected_text_deltas: list[str] = []
        with client.responses.stream(
            model=model,
            store=False,
            instructions=instructions,
            input=input_payload,
        ) as stream:
            for event in stream:
                event_type = getattr(event, "type", "")
                if event_type == "response.output_item.done":
                    item = getattr(event, "item", None)
                    if item is not None:
                        collected_output_items.append(item)
                elif "output_text.delta" in event_type:
                    delta = getattr(event, "delta", "")
                    if delta:
                        collected_text_deltas.append(delta)
            final = stream.get_final_response()
        if final is not None and not getattr(final, "output", None) and collected_output_items:
            final.output = list(collected_output_items)
        text, output_types = self._response_text_and_types(final)
        if not text and collected_text_deltas:
            text = "".join(collected_text_deltas).strip()
            if not output_types:
                output_types = ["message"]
        if final is not None and not getattr(final, "output", None) and text:
            final.output = [SimpleNamespace(
                type="message",
                role="assistant",
                status="completed",
                content=[SimpleNamespace(type="output_text", text=text)],
            )]
        return self._response_text_and_types(final)

    def _save_png_b64(self, b64: str, filename: str) -> Dict[str, Any]:
        data = base64.b64decode(b64)
        path = ARTIFACTS / filename
        path.write_bytes(data)
        info = {"path": str(path), "bytes": len(data)}
        try:
            with Image.open(path) as img:
                info.update({"width": img.width, "height": img.height, "format": img.format})
        except Exception as exc:
            info["image_open_error"] = str(exc)
        return info

    def _stream_image(self, *, prompt: str, filename: str) -> Dict[str, Any]:
        client = codex_openai_client(self.access_token)
        image_b64 = None
        partial_count = 0
        final_output_types: list[str] = []
        final_output_text = ""
        collected_output_items: list[Any] = []
        with client.responses.stream(
            model=self.image_host_model or self.text_model or "gpt-5.4",
            store=False,
            instructions=(
                "Use the image_generation tool to fulfill this request. "
                "Return the generated image."
            ),
            input=[{
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }],
            tools=[{
                "type": "image_generation",
                "model": "gpt-image-2",
                "size": "1024x1024",
                "quality": "low",
            }],
            tool_choice={"type": "image_generation"},
        ) as stream:
            for event in stream:
                event_type = getattr(event, "type", "")
                if event_type == "response.image_generation_call.partial_image":
                    partial_count += 1
                elif event_type == "response.output_item.done":
                    item = getattr(event, "item", None)
                    if item is not None:
                        collected_output_items.append(item)
                        if self._item_get(item, "type") == "image_generation_call":
                            image_b64 = self._item_get(item, "result")
                elif event_type == "response.completed":
                    response = getattr(event, "response", None)
                    for item in getattr(response, "output", []) or []:
                        if self._item_get(item, "type") == "image_generation_call":
                            image_b64 = self._item_get(item, "result")
            if image_b64 is None:
                final = stream.get_final_response()
                if final is not None and not getattr(final, "output", None) and collected_output_items:
                    final.output = list(collected_output_items)
                final_output_text, final_output_types = self._response_text_and_types(final)
                for item in getattr(final, "output", []) or []:
                    if self._item_get(item, "type") == "image_generation_call":
                        image_b64 = self._item_get(item, "result")
        if not image_b64:
            return {
                "host_model": self.image_host_model,
                "image_model": "gpt-image-2",
                "partial_image_events": partial_count,
                "output_types": final_output_types,
                "output_text": final_output_text[:500],
                "reason": "No image_generation_call result was returned.",
                "_status": "expected_blocked",
            }
        saved = self._save_png_b64(image_b64, filename)
        saved.update({
            "host_model": self.image_host_model,
            "image_model": "gpt-image-2",
            "partial_image_events": partial_count,
        })
        if saved.get("bytes", 0) < 1000 or not saved.get("width"):
            saved["_status"] = "fail"
        return saved

    def test_generated_image(self) -> Dict[str, Any]:
        return self._stream_image(
            prompt=(
                "Generate a clean square image showing an OAuth token flowing "
                "from a laptop to a Codex gateway, with no readable text."
            ),
            filename="codex_oauth_image.png",
        )

    def test_generated_drawing(self) -> Dict[str, Any]:
        return self._stream_image(
            prompt=(
                "Draw a simple black ink line-art diagram of a secure OAuth "
                "handshake between a user, Hermes, and Codex. No words."
            ),
            filename="codex_oauth_drawing.png",
        )

    def test_vision_input(self) -> Dict[str, Any]:
        red_png = ARTIFACTS / "vision_probe_red_square.png"
        Image.new("RGB", (32, 32), (255, 0, 0)).save(red_png)
        b64 = base64.b64encode(red_png.read_bytes()).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"
        text, output_types = self._stream_text_response(
            model=self.text_model or "gpt-5.4-mini",
            instructions="Answer image questions briefly and literally.",
            input_payload=[{
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "What is the dominant color in this image? Answer one word."},
                    {"type": "input_image", "image_url": data_url},
                ],
            }],
        )
        text = text.strip()
        return {
            "probe_image": str(red_png),
            "model": self.text_model,
            "output_text": text[:200],
            "output_types": output_types,
            "_status": "pass" if "red" in text.lower() else "fail",
        }

    def _tiny_wav(self) -> Path:
        path = ARTIFACTS / "tiny_silence.wav"
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x00" * 1600)
        return path

    def _official_api_get(self, path: str, *, headers_extra: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        if headers_extra:
            headers.update(headers_extra)
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.get(f"https://api.openai.com{path}", headers=headers)
        evidence = {
            "url": f"https://api.openai.com{path}",
            "http_status": response.status_code,
            "response_prefix": sanitize_response_text(response.text),
            "auth": "Codex OAuth bearer token, redacted",
        }
        evidence["_status"] = self._status_from_official_response(response)
        return evidence

    def _status_from_official_response(self, response: httpx.Response) -> str:
        if 200 <= response.status_code < 300:
            return "pass"
        text = response.text.lower()
        if (
            response.status_code in (401, 403)
            or "missing scopes" in text
            or "missing_scope" in text
            or "insufficient permissions" in text
            or "api key" in text
            or "secret key" in text
            or "invalid authorization" in text
            or "not authorized" in text
        ):
            return "expected_blocked"
        if response.status_code in (400, 409, 422):
            return "auth_accepted_request_invalid"
        if response.status_code == 404:
            return "resource_required" if response.text.strip() else "expected_blocked"
        return "fail"

    def _official_api_post(
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
        evidence = {
            "url": f"https://api.openai.com{path}",
            "http_status": response.status_code,
            "response_prefix": sanitize_response_text(response.text),
            "auth": "Codex OAuth bearer token, redacted",
        }
        evidence["_status"] = self._status_from_official_response(response)
        return evidence

    def _official_api_delete(self, path: str, *, headers_extra: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        if headers_extra:
            headers.update(headers_extra)
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.delete(f"https://api.openai.com{path}", headers=headers)
        evidence = {
            "url": f"https://api.openai.com{path}",
            "http_status": response.status_code,
            "response_prefix": sanitize_response_text(response.text),
            "auth": "Codex OAuth bearer token, redacted",
        }
        evidence["_status"] = self._status_from_official_response(response)
        return evidence

    def test_official_models_list(self) -> Dict[str, Any]:
        return self._official_api_get("/v1/models")

    def test_official_files_list(self) -> Dict[str, Any]:
        return self._official_api_get("/v1/files")

    def test_official_chat_completions(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/chat/completions", json_body={
            "model": self.text_model or "gpt-5.4-mini",
            "messages": [{"role": "user", "content": "Reply with: oauth chat ok"}],
        })

    def test_official_completions_legacy(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/completions", json_body={
            "model": "gpt-3.5-turbo-instruct",
            "prompt": "Reply with: oauth completion ok",
            "max_tokens": 5,
        })

    def test_official_responses_blocked(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/responses", json_body={
            "model": "gpt-5.4-mini",
            "input": "OAuth-only official API probe",
        })

    def test_official_responses_web_search(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/responses", json_body={
            "model": "gpt-5.4-mini",
            "input": "OAuth-only web search tool probe",
            "tools": [{"type": "web_search_preview"}],
        })

    def test_official_image_blocked(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/images/generations", json_body={
            "model": "gpt-image-1",
            "prompt": "small OAuth probe image",
            "size": "1024x1024",
        })

    def test_official_image_edit_probe(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/images/edits", json_body={
            "model": "gpt-image-1.5",
            "prompt": "",
            "images": [],
        })

    def test_official_image_variation_probe(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/images/variations", files={
            "model": (None, "dall-e-2"),
        })

    def test_official_tts_blocked(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/audio/speech", json_body={
            "model": "gpt-4o-mini-tts",
            "voice": "coral",
            "input": "OAuth voice probe.",
        })

    def test_official_stt_blocked(self) -> Dict[str, Any]:
        wav_path = self._tiny_wav()
        with wav_path.open("rb") as fh:
            files = {
                "file": ("tiny_silence.wav", fh, "audio/wav"),
                "model": (None, "gpt-4o-mini-transcribe"),
            }
            return self._official_api_post("/v1/audio/transcriptions", files=files)

    def test_official_translation(self) -> Dict[str, Any]:
        wav_path = self._tiny_wav()
        with wav_path.open("rb") as fh:
            files = {
                "file": ("tiny_silence.wav", fh, "audio/wav"),
                "model": (None, "whisper-1"),
            }
            return self._official_api_post("/v1/audio/translations", files=files)

    def test_official_realtime_blocked(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/realtime/client_secrets", json_body={
            "session": {
                "type": "realtime",
                "model": "gpt-realtime",
            },
        })

    def _create_realtime_client_secret(self) -> str:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.post("https://api.openai.com/v1/realtime/client_secrets", headers=headers, json={
                "session": {
                    "type": "realtime",
                    "model": "gpt-realtime",
                },
            })
        if response.status_code != 200:
            raise RuntimeError(f"Could not create realtime client secret: HTTP {response.status_code} {sanitize_response_text(response.text)}")
        payload = response.json()
        value = payload.get("value")
        if not isinstance(value, str) or not value:
            raise RuntimeError("Realtime client secret response did not contain value.")
        return value

    async def _realtime_audio_probe_async(self) -> Dict[str, Any]:
        secret = self._create_realtime_client_secret()
        uri = "wss://api.openai.com/v1/realtime?model=gpt-realtime"
        audio_chunks: list[bytes] = []
        transcript_parts: list[str] = []
        event_types: list[str] = []
        async with websockets.connect(
            uri,
            additional_headers={
                "Authorization": f"Bearer {secret}",
            },
            open_timeout=15,
            max_size=8 * 1024 * 1024,
        ) as ws:
            await ws.send(json.dumps({
                "type": "response.create",
                "response": {
                    "output_modalities": ["audio"],
                    "instructions": "Say exactly: oauth realtime ok.",
                },
            }))
            deadline = time.time() + 35
            while time.time() < deadline:
                message = await asyncio.wait_for(ws.recv(), timeout=max(1.0, deadline - time.time()))
                event = json.loads(message)
                event_type = str(event.get("type", ""))
                if event_type and event_type not in event_types:
                    event_types.append(event_type)
                if event_type == "error":
                    raise RuntimeError(sanitize_response_text(json.dumps(event.get("error", event)), limit=800))
                delta = event.get("delta")
                if isinstance(delta, str) and "audio" in event_type:
                    try:
                        audio_chunks.append(base64.b64decode(delta))
                    except Exception:
                        pass
                if isinstance(delta, str) and "transcript" in event_type:
                    transcript_parts.append(delta)
                if event_type in {"response.done", "response.completed"}:
                    break
        audio = b"".join(audio_chunks)
        audio_path = ARTIFACTS / "realtime_oauth_audio_response.pcm16"
        transcript_path = ARTIFACTS / "realtime_oauth_audio_transcript.txt"
        if audio:
            audio_path.write_bytes(audio)
        if transcript_parts:
            transcript_path.write_text("".join(transcript_parts))
        return {
            "websocket_url": "wss://api.openai.com/v1/realtime?model=gpt-realtime",
            "audio_path": str(audio_path) if audio else None,
            "audio_bytes": len(audio),
            "transcript_path": str(transcript_path) if transcript_parts else None,
            "transcript": "".join(transcript_parts)[:200],
            "event_types": event_types[:40],
            "_status": "pass" if len(audio) > 100 else "fail",
        }

    def test_official_realtime_audio_websocket(self) -> Dict[str, Any]:
        return asyncio.run(self._realtime_audio_probe_async())

    def test_official_realtime_transcription_session(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/realtime/client_secrets", json_body={
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

    def test_official_realtime_transcription_sessions_legacy_shape(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/realtime/transcription_sessions", json_body={
            "input_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "gpt-4o-mini-transcribe",
            },
        })

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

    def test_official_embeddings_blocked(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/embeddings", json_body={
            "model": "text-embedding-3-small",
            "input": "OAuth embedding probe",
        })

    def test_official_moderation_blocked(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/moderations", json_body={
            "model": "omni-moderation-latest",
            "input": "OAuth moderation probe",
        })

    def test_official_vector_stores_list(self) -> Dict[str, Any]:
        return self._official_api_get("/v1/vector_stores?limit=1")

    def test_official_batches_list(self) -> Dict[str, Any]:
        return self._official_api_get("/v1/batches?limit=1")

    def test_official_fine_tuning_jobs_list(self) -> Dict[str, Any]:
        return self._official_api_get("/v1/fine_tuning/jobs?limit=1")

    def test_official_evals_list(self) -> Dict[str, Any]:
        return self._official_api_get("/v1/evals?limit=1")

    def test_official_containers_list(self) -> Dict[str, Any]:
        return self._official_api_get("/v1/containers?limit=1")

    def test_official_videos_list(self) -> Dict[str, Any]:
        return self._official_api_get("/v1/videos?limit=1")

    def test_official_videos_create_shape_probe(self) -> Dict[str, Any]:
        # Empty body is intentional: it proves whether OAuth reaches the route without starting a Sora job.
        return self._official_api_post("/v1/videos", json_body={})

    def test_official_upload_create_cancel(self) -> Dict[str, Any]:
        path = "/v1/uploads"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "purpose": "assistants",
            "filename": "oauth-probe.txt",
            "bytes": 1,
            "mime_type": "text/plain",
            "expires_after": {"anchor": "created_at", "seconds": 3600},
        }
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.post(f"https://api.openai.com{path}", headers=headers, json=body)
            status = self._status_from_official_response(response)
            upload_id = None
            cancel_status = None
            if 200 <= response.status_code < 300:
                payload = response.json()
                upload_id = payload.get("id")
                if isinstance(upload_id, str) and upload_id:
                    cancel = client.post(f"https://api.openai.com/v1/uploads/{upload_id}/cancel", headers=headers, json={})
                    cancel_status = cancel.status_code
                    if not (200 <= cancel.status_code < 300):
                        status = "fail"
        return {
            "url": "https://api.openai.com/v1/uploads",
            "http_status": response.status_code,
            "upload_id_prefix": upload_id[:12] if isinstance(upload_id, str) else None,
            "cancel_http_status": cancel_status,
            "response_prefix": sanitize_response_text(response.text),
            "auth": "Codex OAuth bearer token, redacted",
            "_status": status,
        }

    def test_official_assistants_list(self) -> Dict[str, Any]:
        return self._official_api_get(
            "/v1/assistants?limit=1",
            headers_extra={"OpenAI-Beta": "assistants=v2"},
        )

    def test_official_thread_create_delete(self) -> Dict[str, Any]:
        path = "/v1/threads"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "OpenAI-Beta": "assistants=v2",
        }
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            response = client.post(f"https://api.openai.com{path}", headers=headers, json={})
            status = self._status_from_official_response(response)
            thread_id = None
            delete_status = None
            if 200 <= response.status_code < 300:
                payload = response.json()
                thread_id = payload.get("id")
                if isinstance(thread_id, str) and thread_id:
                    delete = client.delete(f"https://api.openai.com/v1/threads/{thread_id}", headers=headers)
                    delete_status = delete.status_code
                    if not (200 <= delete.status_code < 300):
                        status = "fail"
        return {
            "url": "https://api.openai.com/v1/threads",
            "http_status": response.status_code,
            "thread_id_prefix": thread_id[:12] if isinstance(thread_id, str) else None,
            "delete_http_status": delete_status,
            "response_prefix": sanitize_response_text(response.text),
            "auth": "Codex OAuth bearer token, redacted",
            "_status": status,
        }

    def test_official_chatkit_session(self) -> Dict[str, Any]:
        workflow_id = os.environ.get("OPENAI_CHATKIT_WORKFLOW_ID", "").strip()
        body = {
            "workflow": {"id": workflow_id or "wf_oauth_probe_missing"},
            "user": "oauth-probe-local",
        }
        evidence = self._official_api_post(
            "/v1/chatkit/sessions",
            json_body=body,
            headers_extra={"OpenAI-Beta": "chatkit_beta=v1"},
        )
        evidence["workflow_id_source"] = "env" if workflow_id else "missing-env-placeholder"
        if not workflow_id and evidence.get("_status") == "auth_accepted_request_invalid":
            evidence["_status"] = "resource_required"
        return evidence

    def test_official_realtime_calls_shape_probe(self) -> Dict[str, Any]:
        return self._official_api_post("/v1/realtime/calls", json_body={})

    def test_official_realtime_calls_valid_sdp(self) -> Dict[str, Any]:
        url = "https://api.openai.com/v1/realtime/calls"
        boundary = "codex-realtime-call-boundary"
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
            f"{self.realistic_webrtc_offer_sdp()}\r\n"
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
        evidence = {
            "url": url,
            "http_status": response.status_code,
            "response_prefix": sanitize_response_text(response.text),
            "auth": "Codex OAuth bearer token, redacted",
            "_status": self._status_from_official_response(response),
        }
        if 200 <= response.status_code < 300:
            location = response.headers.get("location") or ""
            parts = [part for part in location.split("/") if part]
            if parts:
                parts[-1] = "<call-id>"
            evidence.update({
                "location_header_present": bool(location),
                "location_path_shape": "/" + "/".join(parts[-3:]) if parts else None,
                "answer_sdp_present": response.text.startswith("v=0"),
                "answer_sdp_line_count": len(response.text.splitlines()),
                "answer_sdp_sha256_prefix": hashlib.sha256(response.content).hexdigest()[:16],
                "response_prefix": "",
                "_status": "pass",
            })
        return evidence

    def test_official_admin_projects_list(self) -> Dict[str, Any]:
        return self._official_api_get("/v1/organization/projects?limit=1")

    def test_official_admin_users_list(self) -> Dict[str, Any]:
        return self._official_api_get("/v1/organization/users?limit=1")

    def test_official_admin_keys_list(self) -> Dict[str, Any]:
        return self._official_api_get("/v1/organization/admin_api_keys?limit=1")

    def test_official_audit_logs_list(self) -> Dict[str, Any]:
        return self._official_api_get("/v1/organization/audit_logs?limit=1")

    def test_official_usage_completions(self) -> Dict[str, Any]:
        start_time = int(time.time()) - 86400
        return self._official_api_get(f"/v1/organization/usage/completions?start_time={start_time}&limit=1")

    def test_official_costs(self) -> Dict[str, Any]:
        start_time = int(time.time()) - 86400
        return self._official_api_get(f"/v1/organization/costs?start_time={start_time}&limit=1")

    def test_codex_audio_speech_route(self) -> Dict[str, Any]:
        client = codex_openai_client(self.access_token)
        try:
            speech = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="coral",
                input="OAuth Codex backend voice probe.",
            )
            data = bytes(speech.read())
            path = ARTIFACTS / "codex_oauth_tts.mp3"
            path.write_bytes(data)
            return {
                "path": str(path),
                "bytes": len(data),
                "_status": "pass" if len(data) > 1000 else "fail",
            }
        except Exception as exc:
            return {
                "base_url": CODEX_BASE_URL,
                "exception_type": type(exc).__name__,
                "error": sanitize_response_text(str(exc), limit=500),
                "_status": "expected_blocked",
            }

    def write_reports(self) -> None:
        REPORTS.mkdir(exist_ok=True)
        ARTIFACTS.mkdir(exist_ok=True)
        finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        payload = {
            "started_at": self.started_at,
            "finished_at": finished_at,
            "root": str(ROOT),
            "runtime_source": self.runtime_source.name,
            "selected_text_model": self.text_model,
            "selected_image_host_model": self.image_host_model,
            "results": [dataclasses.asdict(r) for r in self.results],
        }
        (REPORTS / "latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))

        lines = [
            "# OAuth Matrix Report",
            "",
            f"- Started: `{self.started_at}`",
            f"- Finished: `{finished_at}`",
            f"- Runtime source: `{self.runtime_source.name}`",
            f"- Text model: `{self.text_model}`",
            f"- Image host model: `{self.image_host_model}`",
            "",
            "| Status | Test | Category | Evidence |",
            "|---|---|---|---|",
        ]
        for result in self.results:
            evidence_bits = []
            for key in (
                "http_status",
                "cancel_http_status",
                "delete_http_status",
                "model_count",
                "model",
                "output_text",
                "path",
                "bytes",
                "width",
                "height",
                "audio_path",
                "audio_bytes",
                "transcript",
                "answer_sdp_present",
                "answer_sdp_line_count",
                "answer_sdp_sha256_prefix",
                "location_header_present",
                "location_path_shape",
                "upload_id_prefix",
                "thread_id_prefix",
                "workflow_id_source",
                "url",
            ):
                value = result.evidence.get(key)
                if value is not None:
                    evidence_bits.append(f"{key}={value}")
            if result.error:
                evidence_bits.append(f"error={result.error[:160]}")
            lines.append(
                f"| `{result.status}` | `{result.name}` | `{result.category}` | "
                f"{'; '.join(str(x) for x in evidence_bits)[:600]} |"
            )
        lines.extend([
            "",
            "## Meaning",
            "",
            "- `pass`: Codex/ChatGPT OAuth reached the surface and produced a usable result.",
            "- `expected_blocked`: The endpoint rejected OAuth as expected or the Codex backend has no route for it.",
            "- `auth_accepted_request_invalid`: OAuth reached the route, then the probe payload or missing object shape was rejected before any expensive job was started.",
            "- `resource_required`: OAuth got far enough that a real workflow/resource ID is needed to continue.",
            "- `fail`: The test should have worked under the current OAuth path but did not.",
            "",
            "No access tokens, refresh tokens, API keys, or Authorization headers are stored in this report.",
        ])
        (REPORTS / "latest.md").write_text("\n".join(lines) + "\n")

    def run(self) -> int:
        REPORTS.mkdir(exist_ok=True)
        ARTIFACTS.mkdir(exist_ok=True)
        self.run_case("token_inventory", "auth", self.test_token_inventory)
        self.run_case("no_platform_api_key_env", "auth", self.test_no_platform_api_key_env)
        self.run_case("codex_models", "codex-oauth", self.test_codex_models)
        self.run_case("codex_text_response", "codex-oauth", self.test_text_response)
        self.run_case("codex_vision_input", "codex-oauth", self.test_vision_input)
        if self.include_images:
            self.run_case("codex_image_generation", "codex-oauth", self.test_generated_image)
            self.run_case("codex_drawing_generation", "codex-oauth", self.test_generated_drawing)
        self.run_case("codex_audio_speech_route", "codex-oauth", self.test_codex_audio_speech_route)
        if self.include_official_negative:
            self.run_case("official_api_models_list_with_oauth", "official-api-oauth", self.test_official_models_list)
            self.run_case("official_api_files_list_with_oauth", "official-api-oauth", self.test_official_files_list)
            self.run_case("official_api_chat_completions_with_oauth", "official-api-oauth", self.test_official_chat_completions)
            self.run_case("official_api_completions_legacy_with_oauth", "official-api-oauth", self.test_official_completions_legacy)
            self.run_case("official_api_responses_with_oauth", "official-api-boundary", self.test_official_responses_blocked)
            self.run_case("official_api_responses_web_search_with_oauth", "official-api-boundary", self.test_official_responses_web_search)
            self.run_case("official_api_image_with_oauth", "official-api-boundary", self.test_official_image_blocked)
            self.run_case("official_api_image_edit_with_oauth", "official-api-boundary", self.test_official_image_edit_probe)
            self.run_case("official_api_image_variation_with_oauth", "official-api-boundary", self.test_official_image_variation_probe)
            self.run_case("official_api_tts_with_oauth", "official-api-boundary", self.test_official_tts_blocked)
            self.run_case("official_api_stt_with_oauth", "official-api-boundary", self.test_official_stt_blocked)
            self.run_case("official_api_translation_with_oauth", "official-api-oauth", self.test_official_translation)
            self.run_case("official_api_realtime_with_oauth", "official-api-boundary", self.test_official_realtime_blocked)
            self.run_case("official_api_realtime_audio_websocket_with_oauth", "official-api-oauth", self.test_official_realtime_audio_websocket)
            self.run_case("official_api_realtime_transcription_with_oauth", "official-api-oauth", self.test_official_realtime_transcription_session)
            self.run_case("official_api_realtime_transcription_sessions_legacy_shape_with_oauth", "official-api-boundary", self.test_official_realtime_transcription_sessions_legacy_shape)
            self.run_case("official_api_realtime_calls_with_oauth", "official-api-oauth", self.test_official_realtime_calls_valid_sdp)
            self.run_case("official_api_realtime_calls_shape_probe_with_oauth", "official-api-boundary", self.test_official_realtime_calls_shape_probe)
            self.run_case("official_api_embeddings_with_oauth", "official-api-boundary", self.test_official_embeddings_blocked)
            self.run_case("official_api_moderation_with_oauth", "official-api-boundary", self.test_official_moderation_blocked)
            self.run_case("official_api_vector_stores_list_with_oauth", "official-api-catalog", self.test_official_vector_stores_list)
            self.run_case("official_api_batches_list_with_oauth", "official-api-catalog", self.test_official_batches_list)
            self.run_case("official_api_fine_tuning_jobs_list_with_oauth", "official-api-catalog", self.test_official_fine_tuning_jobs_list)
            self.run_case("official_api_evals_list_with_oauth", "official-api-catalog", self.test_official_evals_list)
            self.run_case("official_api_containers_list_with_oauth", "official-api-catalog", self.test_official_containers_list)
            self.run_case("official_api_videos_list_with_oauth", "official-api-catalog", self.test_official_videos_list)
            self.run_case("official_api_videos_create_shape_with_oauth", "official-api-catalog", self.test_official_videos_create_shape_probe)
            self.run_case("official_api_upload_create_cancel_with_oauth", "official-api-catalog", self.test_official_upload_create_cancel)
            self.run_case("official_api_assistants_list_with_oauth", "official-api-catalog", self.test_official_assistants_list)
            self.run_case("official_api_thread_create_delete_with_oauth", "official-api-catalog", self.test_official_thread_create_delete)
            self.run_case("official_api_chatkit_session_with_oauth", "official-api-catalog", self.test_official_chatkit_session)
            self.run_case("official_api_admin_projects_list_with_oauth", "admin-api-oauth", self.test_official_admin_projects_list)
            self.run_case("official_api_admin_users_list_with_oauth", "admin-api-oauth", self.test_official_admin_users_list)
            self.run_case("official_api_admin_keys_list_with_oauth", "admin-api-oauth", self.test_official_admin_keys_list)
            self.run_case("official_api_audit_logs_list_with_oauth", "admin-api-oauth", self.test_official_audit_logs_list)
            self.run_case("official_api_usage_completions_with_oauth", "admin-api-oauth", self.test_official_usage_completions)
            self.run_case("official_api_costs_with_oauth", "admin-api-oauth", self.test_official_costs)
        self.write_reports()
        return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-images", action="store_true", help="Skip image/drawing generation.")
    parser.add_argument("--skip-official-negative", action="store_true", help="Skip expected-blocked official API probes.")
    args = parser.parse_args(argv)

    try:
        matrix = Matrix(
            include_images=not args.skip_images,
            include_official_negative=not args.skip_official_negative,
        )
        return matrix.run()
    except Exception:
        REPORTS.mkdir(exist_ok=True)
        err = {
            "fatal": True,
            "traceback": traceback.format_exc(),
        }
        (REPORTS / "latest.json").write_text(json.dumps(err, indent=2))
        print(err["traceback"], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
