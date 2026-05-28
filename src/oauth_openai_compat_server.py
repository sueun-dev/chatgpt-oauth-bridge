from __future__ import annotations

import argparse
import base64
import json
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from oauth_feature_router import ROOT, OAuthFeatureRouter


ARTIFACTS = ROOT / "artifacts"


class CompatHandler(BaseHTTPRequestHandler):
    router: OAuthFeatureRouter

    server_version = "OAuthOpenAICompat/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self.write_json({"ok": True, "route": "oauth_compat_server"})
            return
        self.write_json({"error": {"message": "Not found", "type": "not_found"}}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        try:
            if self.path == "/v1/responses":
                self.handle_responses()
            elif self.path == "/v1/chat/completions":
                self.handle_chat_completions()
            elif self.path == "/v1/embeddings":
                self.handle_embeddings()
            elif self.path == "/v1/images/generations":
                self.handle_images_generations()
            else:
                self.write_json({"error": {"message": "Not found", "type": "not_found"}}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.write_json({
                "error": {
                    "message": str(exc)[:600],
                    "type": type(exc).__name__,
                }
            }, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_responses(self) -> None:
        body = self.read_json()
        input_value = body.get("input", "")
        prompt = self.input_to_text(input_value)
        instructions = body.get("instructions") if isinstance(body.get("instructions"), str) else "Answer directly."
        result = self.router.responses_create(prompt, instructions=instructions)
        response_id = f"resp_oauth_{uuid.uuid4().hex}"
        text = result.get("output_text", "")
        self.write_json({
            "id": response_id,
            "object": "response",
            "created_at": int(time.time()),
            "model": result.get("model"),
            "output_text": text,
            "output": [{
                "id": f"msg_{uuid.uuid4().hex}",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text}],
            }],
            "oauth_compat_route": result.get("route"),
        })

    def handle_chat_completions(self) -> None:
        body = self.read_json()
        messages = body.get("messages")
        if not isinstance(messages, list):
            raise ValueError("messages must be a list")
        result = self.router.chat_completions_create(messages)
        message = result.get("message", {"role": "assistant", "content": ""})
        self.write_json({
            "id": f"chatcmpl_oauth_{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": result.get("model"),
            "choices": [{
                "index": 0,
                "message": message,
                "finish_reason": "stop",
            }],
            "oauth_compat_route": result.get("route"),
        })

    def handle_embeddings(self) -> None:
        body = self.read_json()
        input_value = body.get("input")
        text = self.input_to_text(input_value)
        payload = self.router.embeddings_create(text)
        self.write_json(payload, HTTPStatus.OK if payload.get("_http_status", 200) < 400 else HTTPStatus.BAD_GATEWAY)

    def handle_images_generations(self) -> None:
        body = self.read_json()
        prompt = body.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        size = body.get("size", "1024x1024")
        if size not in {"1024x1024", "1536x1024", "1024x1536", "auto"}:
            raise ValueError("size must be one of 1024x1024, 1536x1024, 1024x1536, auto")
        ARTIFACTS.mkdir(exist_ok=True)
        output_path = ARTIFACTS / f"compat_proxy_image_{uuid.uuid4().hex}.png"
        result = self.router.images_generate(prompt, output_path, size=size)
        image_bytes = Path(result["path"]).read_bytes()
        item: Dict[str, Any]
        if body.get("response_format") == "url":
            item = {"url": f"file://{result['path']}"}
        else:
            item = {"b64_json": base64.b64encode(image_bytes).decode("ascii")}
        self.write_json({
            "created": int(time.time()),
            "data": [item],
            "oauth_compat_route": result.get("route"),
            "size": result.get("size"),
            "local_path": result.get("path"),
        })

    def input_to_text(self, input_value: Any) -> str:
        if isinstance(input_value, str):
            return input_value
        if isinstance(input_value, list):
            chunks = []
            for item in input_value:
                if isinstance(item, str):
                    chunks.append(item)
                elif isinstance(item, dict):
                    role = item.get("role")
                    content = item.get("content")
                    text_parts = []
                    if isinstance(content, str):
                        text_parts.append(content)
                    elif isinstance(content, list):
                        for content_item in content:
                            if isinstance(content_item, dict):
                                text = content_item.get("text") or content_item.get("input_text")
                                if isinstance(text, str):
                                    text_parts.append(text)
                    prefix = f"{role}: " if isinstance(role, str) else ""
                    if text_parts:
                        chunks.append(prefix + "\n".join(text_parts))
            return "\n".join(chunks)
        return str(input_value)

    def read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def write_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def make_server(host: str, port: int) -> ThreadingHTTPServer:
    CompatHandler.router = OAuthFeatureRouter()
    return ThreadingHTTPServer((host, port), CompatHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local OpenAI-compatible OAuth-only proxy.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    server = make_server(args.host, args.port)
    print(json.dumps({
        "host": args.host,
        "port": server.server_address[1],
        "base_url": f"http://{args.host}:{server.server_address[1]}/v1",
        "routes": [
            "/v1/responses",
            "/v1/chat/completions",
            "/v1/embeddings",
            "/v1/images/generations",
        ],
    }, indent=2))
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
