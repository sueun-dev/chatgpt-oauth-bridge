from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from environment_probe import build_report as build_environment_report
from environment_probe import write_reports as write_environment_reports


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def run_command(name: str, command: List[str]) -> Dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("PYTHONPYCACHEPREFIX", str(ROOT / ".pycache"))
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {
        "name": name,
        "status": "pass" if proc.returncode == 0 else "fail",
        "returncode": proc.returncode,
        "command": " ".join(command),
        "output": proc.stdout.strip()[-4000:],
    }


def skipped(name: str, reason: str) -> Dict[str, Any]:
    return {
        "name": name,
        "status": "skipped",
        "returncode": None,
        "command": None,
        "output": reason,
    }


def environment_ok(payload: Dict[str, Any]) -> bool:
    token = payload.get("token_source") if isinstance(payload.get("token_source"), dict) else {}
    model = payload.get("codex_model_discovery") if isinstance(payload.get("codex_model_discovery"), dict) else {}
    bind = payload.get("localhost_bind") if isinstance(payload.get("localhost_bind"), dict) else {}
    return token.get("ok") is True and model.get("ok") is True and bind.get("ok") is True


def build_report(
    *,
    host: str,
    port: int,
    timeout_seconds: float,
    include_images: bool,
    skip_speech: bool,
    force: bool,
    write_dependencies: bool = True,
) -> Dict[str, Any]:
    environment = build_environment_report(host, port, timeout_seconds)
    if write_dependencies:
        write_environment_reports(environment)
    env_ok = environment_ok(environment)
    checks: List[Dict[str, Any]] = [{
        "name": "environment_probe",
        "status": "pass" if env_ok else "fail",
        "returncode": 0 if env_ok else 1,
        "command": f"{sys.executable} src/environment_probe.py --host {host} --port {port} --timeout {timeout_seconds}",
        "output": (
            f"token_source_ok={(environment.get('token_source') or {}).get('ok')}; "
            f"codex_model_discovery_ok={(environment.get('codex_model_discovery') or {}).get('ok')}; "
            f"codex_model_discovery_error_type={(environment.get('codex_model_discovery') or {}).get('error_type')}; "
            f"localhost_bind_ok={(environment.get('localhost_bind') or {}).get('ok')}; "
            f"localhost_bind_error_type={(environment.get('localhost_bind') or {}).get('error_type')}"
        ),
    }]

    smoke_args = [sys.executable, "src/run_proxy_smoke.py", "--host", host, "--port", str(port)]
    sdk_args = [sys.executable, "src/run_openai_sdk_proxy_smoke.py", "--host", host, "--port", str(port)]
    if include_images:
        smoke_args.append("--include-images")
        sdk_args.append("--include-images")
    if skip_speech:
        smoke_args.append("--skip-speech")
        sdk_args.append("--skip-speech")
    if not write_dependencies:
        smoke_args.append("--no-write")
        sdk_args.append("--no-write")

    if env_ok or force:
        checks.append(run_command("http_proxy_smoke", smoke_args))
        checks.append(run_command("openai_python_sdk_smoke", sdk_args))
        no_write = [] if write_dependencies else ["--no-write"]
        checks.append(run_command("readiness_report", [sys.executable, "src/readiness_report.py", *no_write]))
        checks.append(run_command("doctor_strict", [sys.executable, "src/doctor_report.py", "--strict", *no_write]))
    else:
        reason = "Skipped because current environment cannot prove Codex model discovery and localhost bind."
        checks.append(skipped("http_proxy_smoke", reason))
        checks.append(skipped("openai_python_sdk_smoke", reason))
        no_write = [] if write_dependencies else ["--no-write"]
        checks.append(run_command("readiness_report", [sys.executable, "src/readiness_report.py", *no_write]))
        checks.append(run_command("doctor_strict", [sys.executable, "src/doctor_report.py", "--strict", *no_write]))

    blocking = [check for check in checks if check["status"] == "fail"]
    skipped_checks = [check for check in checks if check["status"] == "skipped"]
    ok = not blocking and not skipped_checks
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "object": "oauth_compat.live_launch_check",
        "ok": ok,
        "bottom_line": (
            "Live launch check passed: environment, HTTP proxy smoke, SDK smoke, readiness, and strict doctor all passed."
            if ok
            else "Live launch check did not pass. See failed or skipped checks before making launch-ready claims."
        ),
        "host": host,
        "port": port,
        "timeout_seconds": timeout_seconds,
        "include_images": include_images,
        "skip_speech": skip_speech,
        "force": force,
        "environment": environment,
        "checks": checks,
        "next_actions": next_actions(environment, checks),
    }


def next_actions(environment: Dict[str, Any], checks: List[Dict[str, Any]]) -> List[str]:
    actions: List[str] = []
    model = environment.get("codex_model_discovery") if isinstance(environment.get("codex_model_discovery"), dict) else {}
    bind = environment.get("localhost_bind") if isinstance(environment.get("localhost_bind"), dict) else {}
    token = environment.get("token_source") if isinstance(environment.get("token_source"), dict) else {}
    diagnostics = environment.get("diagnostics") if isinstance(environment.get("diagnostics"), dict) else {}
    if token.get("ok") is not True:
        actions.append("Run python bridge.py setup and complete Codex/ChatGPT OAuth login first.")
    if diagnostics.get("dns_or_network_blocked") is True:
        actions.append("DNS/network is blocked in this shell; run from a shell that can resolve chatgpt.com, github.com, and api.openai.com.")
    elif model.get("ok") is not True:
        actions.append("Run this command from a shell with network access to chatgpt.com before relying on model-backed calls.")
    if diagnostics.get("localhost_socket_denied") is True:
        actions.append("This shell denies socket bind with PermissionError; use a normal local shell for live HTTP/SDK smoke.")
    elif bind.get("ok") is not True:
        actions.append("Run this command from a shell that can bind localhost, or choose an allowed host/port with --host and --port.")
    for check in checks:
        if check.get("status") == "fail" and check.get("name") not in {"environment_probe"}:
            actions.append(f"Inspect {check.get('name')} output in reports/live_check_latest.md and rerun after fixing it.")
    if not actions:
        actions.append("Use python bridge.py verdict and reports/goal_audit_latest.md as the launch go/no-go record.")
    return actions


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "live_check_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    lines = [
        "# OAuth Bridge Live Launch Check",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- OK: `{payload['ok']}`",
        f"- Bottom line: {payload['bottom_line']}",
        f"- Host: `{payload['host']}`",
        f"- Port: `{payload['port']}`",
        f"- Include images: `{payload['include_images']}`",
        f"- Skip speech: `{payload['skip_speech']}`",
        "",
        "## Environment",
        "",
        "| Check | OK | Evidence |",
        "|---|---|---|",
    ]
    environment = payload["environment"]
    token = environment.get("token_source") if isinstance(environment.get("token_source"), dict) else {}
    model = environment.get("codex_model_discovery") if isinstance(environment.get("codex_model_discovery"), dict) else {}
    bind = environment.get("localhost_bind") if isinstance(environment.get("localhost_bind"), dict) else {}
    lines.append(f"| Token source | `{token.get('ok')}` | `source={token.get('source')}; error={token.get('error')}` |")
    lines.append(f"| Codex model discovery | `{model.get('ok')}` | `http_status={model.get('http_status')}; model_count={model.get('model_count')}; error={model.get('error')}` |")
    lines.append(f"| Localhost bind | `{bind.get('ok')}` | `host={bind.get('host')}; port={bind.get('port')}; error={bind.get('error')}` |")
    lines.extend([
        "",
        "## Checks",
        "",
        "| Status | Check | Return Code | Command | Evidence |",
        "|---|---|---:|---|---|",
    ])
    for check in payload["checks"]:
        output = str(check.get("output") or "").replace("\n", " ")[:500]
        lines.append(
            f"| `{check.get('status')}` | `{check.get('name')}` | `{check.get('returncode')}` | "
            f"`{check.get('command')}` | {output} |"
        )
    lines.extend([
        "",
        "## Next Actions",
        "",
    ])
    for action in payload["next_actions"]:
        lines.append(f"- {action}")
    lines.append("")
    (REPORTS / "live_check_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any]) -> None:
    print("OAuth bridge live launch check:", "pass" if payload["ok"] else "fail")
    print(payload["bottom_line"])
    for check in payload["checks"]:
        print(f"- {check['status']}: {check['name']}")
        if check.get("output") and check["status"] != "pass":
            print("  " + str(check["output"]).replace("\n", "\n  ")[:1200])
    if payload["next_actions"]:
        print("Next actions:")
        for action in payload["next_actions"]:
            print(f"- {action}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the live launch gate for the OAuth bridge.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="Use 0 for ephemeral smoke-test ports.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Network timeout for Codex model discovery.")
    parser.add_argument("--include-images", action="store_true", help="Also verify image generation in live smokes.")
    parser.add_argument("--skip-speech", action="store_true", help="Skip Realtime PCM16/audio speech live routes.")
    parser.add_argument("--force", action="store_true", help="Run live smokes even when the environment probe fails.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/live_check_latest.*.")
    args = parser.parse_args()

    payload = build_report(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout,
        include_images=args.include_images,
        skip_speech=args.skip_speech,
        force=args.force,
        write_dependencies=not args.no_write,
    )
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
