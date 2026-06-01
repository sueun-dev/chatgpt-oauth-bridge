from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from environment_probe import build_report as build_environment_report
from environment_probe import write_reports as write_environment_reports
from generate_client_config import build_report as build_client_config_report
from generate_client_config import write_reports as write_client_config_reports
from generate_compatibility_guide import build_report as build_compatibility_guide_report
from generate_compatibility_guide import write_reports as write_compatibility_guide_reports
from readiness_report import build_report as build_readiness_report
from readiness_report import write_reports as write_readiness_reports
from platform_fallback import global_fallback_state


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def git_summary() -> Dict[str, Any]:
    proc = subprocess.run(
        ["git", "status", "--short", "--branch"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    branch = lines[0] if lines else ""
    changed = [line for line in lines[1:] if line.startswith((" M", "M ", "A ", "D ", "R ", "C ", "??"))]
    return {
        "ok": proc.returncode == 0,
        "branch": branch,
        "changed_count": len(changed),
        "sample": changed[:20],
    }


def build_report(
    *,
    host: str,
    port: int,
    timeout_seconds: float,
    refresh_env: bool,
    write_dependencies: bool = True,
) -> Dict[str, Any]:
    git = git_summary()
    if refresh_env:
        environment = build_environment_report(host, 0, timeout_seconds)
        if write_dependencies:
            write_environment_reports(environment)
    guide = build_compatibility_guide_report()
    if write_dependencies:
        write_compatibility_guide_reports(guide)
    client_config = build_client_config_report(host=host, port=port)
    if write_dependencies:
        write_client_config_reports(client_config)
    readiness = build_readiness_report()
    if write_dependencies:
        write_readiness_reports(readiness)

    reports = readiness.get("reports") if isinstance(readiness.get("reports"), dict) else {}
    surface = readiness.get("surface_audit") if isinstance(readiness.get("surface_audit"), dict) else {}
    counts = surface.get("category_counts") if isinstance(surface.get("category_counts"), dict) else {}
    env_report = reports.get("environment") if isinstance(reports.get("environment"), dict) else {}

    direct = int(counts.get("direct_official_oauth_verified", 0) or 0)
    local = int(counts.get("local_compat_or_chatgpt_backend_bridge", 0) or 0)
    boundary = int(counts.get("api_key_or_admin_key_required", 0) or 0)
    unfinished = (
        int(counts.get("resource_bound_not_fully_verified", 0) or 0)
        + int(counts.get("official_route_auth_reached_but_not_complete", 0) or 0)
        + int(counts.get("not_available_current_deployment", 0) or 0)
        + int(counts.get("not_probed_directly", 0) or 0)
    )

    next_actions = [
        "Use python bridge.py quickstart for the first-run bundle: env, CI gate, route policy, and full-goal verdict.",
        "Use python bridge.py live-check from a normal local shell for the launch gate: environment, HTTP proxy smoke, SDK smoke, readiness, and strict doctor.",
        "Use python bridge.py migrate path/to/your/app --fail-on-boundary for a paste-ready migration plan.",
        "Use python bridge.py verdict for the full-goal completion audit and user-facing go/no-go answer.",
        "Use python bridge.py coverage for product-group coverage and boundary decisions.",
        "Use python bridge.py policy for a machine-readable allow/deny/fallback route policy.",
        "Use python bridge.py boundaries for a safe playbook covering every remaining Platform/Admin boundary.",
        "Use python bridge.py fallback to inspect optional Platform/Admin credential forwarding state.",
        "Use python bridge.py check path/to/your/app --fail-on-boundary before migrating an app.",
        "Use python bridge.py config for SDK/curl/env snippets.",
        "Use python bridge.py serve --port 8787 in a normal local shell when localhost binding is allowed.",
    ]
    if boundary:
        next_actions.append(
            "Use official Platform credentials for API/Admin-key boundary paths; do not route them through ChatGPT/Codex OAuth."
        )
    if env_report.get("codex_model_discovery_ok") is not True:
        next_actions.insert(0, "Run from an environment with network access before relying on live model-backed calls.")
    if env_report.get("localhost_bind_ok") is not True:
        next_actions.insert(0, "Run live HTTP/SDK smoke from a shell that can bind localhost.")

    if git.get("changed_count"):
        next_actions.insert(0, "Run python bridge.py publish-check before claiming GitHub or clone users have the latest bridge.")

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "goal_complete": readiness.get("goal_complete"),
        "bottom_line": readiness.get("bottom_line"),
        "base_url": client_config.get("base_url"),
        "placeholder_api_key": client_config.get("placeholder_api_key"),
        "category_counts": counts,
        "usable_without_platform_key": direct + local,
        "platform_credential_boundary": boundary,
        "unfinished_or_not_available": unfinished,
        "environment": env_report,
        "platform_fallback": global_fallback_state(),
        "smoke_reports": {
            "offline": reports.get("offline_smoke"),
            "http_proxy": reports.get("proxy_smoke"),
            "openai_python_sdk": reports.get("sdk_smoke"),
            "oauth_matrix": reports.get("oauth_matrix"),
        },
        "commands": client_config.get("commands"),
        "metadata_endpoints": client_config.get("metadata_endpoints"),
        "next_actions": next_actions,
        "git": git,
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "status_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    lines = [
        "# OAuth Bridge Status",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Goal complete: `{payload['goal_complete']}`",
        f"- Bottom line: {payload['bottom_line']}",
        f"- Base URL: `{payload['base_url']}`",
        f"- Placeholder API key: `{payload['placeholder_api_key']}`",
        "",
        "## Coverage",
        "",
        "| Category | Paths |",
        "|---|---:|",
    ]
    for category, count in sorted(payload["category_counts"].items()):
        lines.append(f"| `{category}` | {count} |")
    lines.extend([
        "",
        "## Current Environment",
        "",
        "| Check | Value |",
        "|---|---|",
    ])
    env = payload["environment"]
    lines.append(f"| Codex model discovery | `{env.get('codex_model_discovery_ok')}` |")
    lines.append(f"| Codex model discovery error | `{env.get('codex_model_discovery_error_type')}` |")
    lines.append(f"| Localhost bind | `{env.get('localhost_bind_ok')}` |")
    lines.append(f"| Localhost bind error | `{env.get('localhost_bind_error_type')}` |")
    lines.append(f"| DNS/network blocked | `{env.get('dns_or_network_blocked')}` |")
    lines.append(f"| Localhost socket denied | `{env.get('localhost_socket_denied')}` |")
    lines.append(f"| Environment report time | `{env.get('finished_at')}` |")
    fallback = payload.get("platform_fallback") if isinstance(payload.get("platform_fallback"), dict) else {}
    lines.extend([
        "",
        "## Platform Fallback",
        "",
        "| Check | Value |",
        "|---|---|",
        f"| Enabled | `{fallback.get('enabled')}` |",
        f"| Mode | `{fallback.get('mode')}` |",
        f"| API key present | `{fallback.get('api_key_present')}` |",
        f"| Access token present | `{fallback.get('access_token_present')}` |",
        f"| Admin key present | `{fallback.get('admin_key_present')}` |",
    ])
    lines.extend([
        "",
        "## Smoke Evidence",
        "",
        "| Report | Results | All Pass | Finished |",
        "|---|---:|---|---|",
    ])
    for name, report in payload["smoke_reports"].items():
        report = report if isinstance(report, dict) else {}
        lines.append(
            f"| `{name}` | {report.get('results')} | `{report.get('all_pass')}` | `{report.get('finished_at')}` |"
        )
    lines.extend([
        "",
        "## Commands",
        "",
    ])
    for name, command in (payload.get("commands") or {}).items():
        lines.append(f"- `{name}`: `{command}`")
    lines.extend([
        "",
        "## Next Actions",
        "",
    ])
    for action in payload["next_actions"]:
        lines.append(f"- {action}")
    git = payload["git"]
    lines.extend([
        "",
        "## Git",
        "",
        f"- Branch: `{git.get('branch')}`",
        f"- Changed files: `{git.get('changed_count')}`",
    ])
    for item in git.get("sample") or []:
        lines.append(f"- `{item}`")
    lines.append("")
    (REPORTS / "status_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any]) -> None:
    print("OAuth bridge status:", "complete" if payload["goal_complete"] else "not complete")
    print(payload["bottom_line"])
    print()
    print(f"base_url={payload['base_url']}")
    print(f"placeholder_api_key={payload['placeholder_api_key']}")
    print(
        "coverage="
        f"direct_oauth={payload['category_counts'].get('direct_official_oauth_verified', 0)}; "
        f"local_bridge={payload['category_counts'].get('local_compat_or_chatgpt_backend_bridge', 0)}; "
        f"platform_boundary={payload['platform_credential_boundary']}; "
        f"unfinished={payload['unfinished_or_not_available']}"
    )
    env = payload["environment"]
    print(
        "environment="
        f"codex_model_discovery_ok={env.get('codex_model_discovery_ok')}; "
        f"codex_model_discovery_error_type={env.get('codex_model_discovery_error_type')}; "
        f"localhost_bind_ok={env.get('localhost_bind_ok')}; "
        f"localhost_bind_error_type={env.get('localhost_bind_error_type')}; "
        f"dns_or_network_blocked={env.get('dns_or_network_blocked')}; "
        f"localhost_socket_denied={env.get('localhost_socket_denied')}"
    )
    fallback = payload.get("platform_fallback") if isinstance(payload.get("platform_fallback"), dict) else {}
    print(
        "platform_fallback="
        f"enabled={fallback.get('enabled')}; "
        f"mode={fallback.get('mode')}; "
        f"api_key_present={fallback.get('api_key_present')}; "
        f"access_token_present={fallback.get('access_token_present')}; "
        f"admin_key_present={fallback.get('admin_key_present')}"
    )
    print(f"git_changed_files={payload['git'].get('changed_count')}")
    print()
    print("Next actions:")
    for action in payload["next_actions"][:5]:
        print(f"- {action}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a one-screen OAuth bridge dashboard for users.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--no-refresh-env", action="store_true", help="Use the latest environment report instead of probing now.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/status_latest.* or dependency reports.")
    args = parser.parse_args()

    payload = build_report(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout,
        refresh_env=not args.no_refresh_env,
        write_dependencies=not args.no_write,
    )
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
