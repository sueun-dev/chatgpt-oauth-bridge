from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from oauth_feature_router import OAuthFeatureRouter


def read_payload(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    messages = payload.get("messages")
    if not isinstance(messages, list):
        raise ValueError("payload.messages must be a list")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Codex OAuth text generation without the local HTTP bridge.")
    parser.add_argument("--input", required=True, help="Path to a JSON file with {messages:[...]}.")
    args = parser.parse_args()

    payload = read_payload(Path(args.input))
    messages: List[Dict[str, str]] = payload["messages"]
    result = OAuthFeatureRouter().chat_completions_create(messages)
    message = result.get("message", {"role": "assistant", "content": ""})
    output = {
        "id": f"chatcmpl_oauth_cli_{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": result.get("model"),
        "choices": [{
            "index": 0,
            "message": message,
            "finish_reason": "stop",
        }],
        "oauth_compat_route": result.get("route"),
    }
    sys.stdout.write(json.dumps(output, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
