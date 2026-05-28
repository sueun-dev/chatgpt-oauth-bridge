from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from oauth_feature_router import OAuthFeatureRouter


def read_payload(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("payload.prompt must be a non-empty string")
    size = payload.get("size", "1024x1024")
    allowed_sizes = {"1024x1024", "1536x1024", "1024x1536", "auto"}
    if size not in allowed_sizes:
        raise ValueError(f"payload.size must be one of {sorted(allowed_sizes)}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Codex OAuth image generation without the local HTTP bridge.")
    parser.add_argument("--input", required=True, help="Path to a JSON file with {prompt:\"...\"}.")
    parser.add_argument("--output", required=True, help="PNG output path.")
    args = parser.parse_args()

    payload = read_payload(Path(args.input))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = OAuthFeatureRouter().images_generate(payload["prompt"], output_path, size=payload.get("size", "1024x1024"))
    sys.stdout.write(json.dumps({
        "ok": True,
        "route": result.get("route"),
        "size": result.get("size"),
        "path": result.get("path") or str(output_path),
        "bytes": output_path.stat().st_size,
    }, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
