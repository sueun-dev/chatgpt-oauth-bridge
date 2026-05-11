from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from codex_oauth import (  # noqa: E402
        OAuthProbeError,
        choose_image_host_model,
        choose_runtime_source,
        choose_text_model,
        fetch_codex_models,
        load_sources,
        token_metadata,
    )
    from openai_oauth_access import OpenAIOAuthAccess  # noqa: E402
except ModuleNotFoundError as exc:
    missing = exc.name or "a Python dependency"
    print(f"Missing Python dependency: {missing}")
    print()
    print("Install dependencies first:")
    print("  python3 -m venv .venv")
    print("  source .venv/bin/activate")
    print("  pip install -r requirements.txt")
    print("  python setup_oauth.py")
    raise SystemExit(2) from exc


def home_relative(path: str) -> str:
    home = str(Path.home())
    if path == home:
        return "~"
    if path.startswith(home + "/"):
        return "~/" + path[len(home) + 1 :]
    return path


def command_status(command: str, args: list[str]) -> dict[str, Any]:
    binary = shutil.which(command)
    if not binary:
        return {"installed": False, "command": command}
    try:
        proc = subprocess.run(
            [binary, *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
            check=False,
        )
    except Exception as exc:
        return {"installed": True, "command": command, "ok": False, "output": str(exc)}
    return {
        "installed": True,
        "command": command,
        "ok": proc.returncode == 0,
        "output": proc.stdout.strip()[:1200],
    }


def safe_source_summary() -> list[dict[str, Any]]:
    rows = []
    for source in load_sources():
        meta = token_metadata(source)
        meta["path"] = home_relative(str(source.path))
        meta.pop("token_prefix", None)
        rows.append(meta)
    return rows


def build_report(*, smoke_text: bool) -> dict[str, Any]:
    sources = load_sources()
    source = choose_runtime_source(sources)
    models = fetch_codex_models(source.access_token or "")
    report: dict[str, Any] = {
        "ok": True,
        "selected_source": source.name,
        "selected_source_path": home_relative(str(source.path)),
        "text_model": choose_text_model(models),
        "image_host_model": choose_image_host_model(models),
        "model_count": len(models),
        "token_sources": safe_source_summary(),
        "cli_status": {
            "codex": command_status("codex", ["login", "status"]),
            "hermes": command_status("hermes", ["auth", "status", "openai-codex"]),
        },
        "next_steps": [
            "Run: PYTHONPATH=src python src/openai_oauth_access.py",
            "Try examples in USAGE_EXAMPLES.md",
            "Start the local proxy with: PYTHONPATH=src python src/oauth_openai_compat_server.py --port 8787",
        ],
    }
    if smoke_text:
        oauth = OpenAIOAuthAccess()
        report["text_smoke"] = oauth.codex_text("Reply exactly: oauth setup ok")
    return report


def print_human(report: dict[str, Any]) -> None:
    if not report.get("ok"):
        print("OAuth is not connected yet.")
        print()
        print(report.get("error", "Unknown error"))
        print()
        print("Fastest setup:")
        print("  codex login --device-auth")
        print("  python setup_oauth.py")
        print()
        print("Hermes alternative:")
        print("  hermes login --provider openai-codex")
        print("  python setup_oauth.py")
        return

    print("OAuth connection is ready.")
    print(f"  selected source: {report['selected_source']} ({report['selected_source_path']})")
    print(f"  models visible:  {report['model_count']}")
    print(f"  text model:      {report['text_model']}")
    print(f"  image host:      {report['image_host_model']}")
    if "text_smoke" in report:
        print(f"  text smoke:      {report['text_smoke']}")
    print()
    print("Token sources:")
    for item in report["token_sources"]:
        print(
            f"  - {item['source']}: exists={item['exists']} "
            f"access={item['has_access_token']} refresh={item['has_refresh_token']} "
            f"seconds_remaining={item['access_token_seconds_remaining']}"
        )
    print()
    print("Next:")
    for step in report["next_steps"]:
        print(f"  - {step}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check and validate ChatGPT/Codex OAuth setup.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable JSON report.")
    parser.add_argument("--no-smoke", action="store_true", help="Skip the text generation smoke test.")
    args = parser.parse_args()

    try:
        report = build_report(smoke_text=not args.no_smoke)
    except OAuthProbeError as exc:
        report = {
            "ok": False,
            "error": str(exc),
            "token_sources": safe_source_summary(),
            "cli_status": {
                "codex": command_status("codex", ["login", "status"]),
                "hermes": command_status("hermes", ["auth", "status", "openai-codex"]),
            },
        }
    except Exception as exc:
        report = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(report)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
