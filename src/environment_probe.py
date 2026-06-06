from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path
from typing import Any, Dict

import httpx

from codex_oauth import CODEX_MODELS_URL, choose_runtime_source, codex_headers, load_sources, token_metadata


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def safe_token_source() -> Dict[str, Any]:
    try:
        source = choose_runtime_source(load_sources())
    except Exception as exc:
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:600],
        }
    meta = token_metadata(source)
    meta.pop("token_prefix", None)
    return {
        "ok": True,
        "source": source.name,
        "path": str(source.path),
        "has_access_token": bool(source.access_token),
        "has_refresh_token": bool(source.refresh_token),
        "access_token_seconds_remaining": meta.get("access_token_seconds_remaining"),
        "_access_token": source.access_token or "",
    }


def probe_codex_models(access_token: str, timeout_seconds: float) -> Dict[str, Any]:
    if not access_token:
        return {"ok": False, "error_type": "missing_token", "error": "No access token available."}
    try:
        with httpx.Client(headers=codex_headers(access_token), timeout=httpx.Timeout(timeout_seconds)) as client:
            response = client.get(CODEX_MODELS_URL)
        model_count = 0
        if response.status_code == 200:
            payload = response.json()
            models = payload.get("models")
            model_count = len(models) if isinstance(models, list) else 0
        return {
            "ok": response.status_code == 200,
            "http_status": response.status_code,
            "model_count": model_count,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:600],
        }


def probe_localhost_bind(host: str, port: int) -> Dict[str, Any]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        bound_host, bound_port = sock.getsockname()
        return {
            "ok": True,
            "host": bound_host,
            "port": bound_port,
        }
    except Exception as exc:
        return {
            "ok": False,
            "host": host,
            "port": port,
            "error_type": type(exc).__name__,
            "error": str(exc)[:600],
        }
    finally:
        sock.close()


def build_report(host: str, port: int, timeout_seconds: float) -> Dict[str, Any]:
    source = safe_token_source()
    access_token = source.pop("_access_token", "") if isinstance(source.get("_access_token"), str) else ""
    model = probe_codex_models(access_token, timeout_seconds)
    bind = probe_localhost_bind(host, port)
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "token_source": source,
        "codex_model_discovery": model,
        "localhost_bind": bind,
        "diagnostics": environment_diagnostics(source, model, bind),
    }


def environment_diagnostics(source: Dict[str, Any], model: Dict[str, Any], bind: Dict[str, Any]) -> Dict[str, Any]:
    model_error = str(model.get("error") or "")
    bind_error = str(bind.get("error") or "")
    dns_blocked = model.get("error_type") == "ConnectError" and "nodename nor servname" in model_error
    bind_denied = bind.get("error_type") == "PermissionError" or "Operation not permitted" in bind_error
    actions = []
    if source.get("ok") is not True:
        actions.append("Complete Codex/ChatGPT OAuth login before running live checks.")
    if dns_blocked:
        actions.append("Run from a shell with DNS/network access to chatgpt.com, github.com, and api.openai.com.")
    elif model.get("ok") is not True:
        actions.append("Run from a shell that can reach ChatGPT/Codex model discovery.")
    if bind_denied:
        actions.append("Run from a normal local shell; this sandbox denies socket bind for every localhost port.")
    elif bind.get("ok") is not True:
        actions.append("Try a different --host/--port or free the occupied port before live HTTP/SDK smoke.")
    return {
        "dns_or_network_blocked": dns_blocked,
        "localhost_socket_denied": bind_denied,
        "live_environment_ok": source.get("ok") is True and model.get("ok") is True and bind.get("ok") is True,
        "next_actions": actions,
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "environment_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    lines = [
        "# OAuth Bridge Environment Probe",
        "",
        f"- Generated: `{payload['generated_at']}`",
        "",
        "## Checks",
        "",
        "| Check | OK | Evidence |",
        "|---|---|---|",
    ]
    source = payload["token_source"]
    lines.append(
        f"| Token source | `{source.get('ok')}` | "
        f"`source={source.get('source')}; has_access_token={source.get('has_access_token')}; "
        f"seconds_remaining={source.get('access_token_seconds_remaining')}; "
        f"error={source.get('error')}` |"
    )
    model = payload["codex_model_discovery"]
    lines.append(
        f"| Codex model discovery | `{model.get('ok')}` | "
        f"`http_status={model.get('http_status')}; model_count={model.get('model_count')}; "
        f"error_type={model.get('error_type')}; error={model.get('error')}` |"
    )
    bind = payload["localhost_bind"]
    lines.append(
        f"| Localhost bind | `{bind.get('ok')}` | "
        f"`host={bind.get('host')}; port={bind.get('port')}; "
        f"error_type={bind.get('error_type')}; error={bind.get('error')}` |"
    )
    diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
    lines.extend([
        "",
        "## Diagnostics",
        "",
        f"- DNS/network blocked: `{diagnostics.get('dns_or_network_blocked')}`",
        f"- Localhost socket denied: `{diagnostics.get('localhost_socket_denied')}`",
        f"- Live environment OK: `{diagnostics.get('live_environment_ok')}`",
        "",
        "## Next Actions",
    ])
    actions = diagnostics.get("next_actions") or []
    if actions:
        lines.append("")
        for action in actions:
            lines.append(f"- {action}")
    else:
        lines.append("")
        lines.append("- None.")
    (REPORTS / "environment_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any]) -> None:
    print("OAuth bridge environment:")
    source = payload["token_source"]
    print(f"- token_source: ok={source.get('ok')} source={source.get('source')} seconds_remaining={source.get('access_token_seconds_remaining')}")
    model = payload["codex_model_discovery"]
    print(f"- codex_model_discovery: ok={model.get('ok')} status={model.get('http_status')} model_count={model.get('model_count')} error_type={model.get('error_type')} error={model.get('error')}")
    bind = payload["localhost_bind"]
    print(f"- localhost_bind: ok={bind.get('ok')} host={bind.get('host')} port={bind.get('port')} error_type={bind.get('error_type')} error={bind.get('error')}")
    diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
    print(f"- diagnostics: dns_or_network_blocked={diagnostics.get('dns_or_network_blocked')} localhost_socket_denied={diagnostics.get('localhost_socket_denied')} live_environment_ok={diagnostics.get('live_environment_ok')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe current local environment limits for the OAuth bridge.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=5.0, help="Network timeout for Codex model discovery.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/environment_latest.*.")
    args = parser.parse_args()

    payload = build_report(args.host, args.port, args.timeout)
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
