from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from platform_fallback import global_fallback_state


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
        "output": proc.stdout.strip()[-2500:],
    }


def load_json(name: str) -> Dict[str, Any]:
    path = REPORTS / name
    if not path.exists():
        return {"_missing": True, "_path": str(path)}
    try:
        payload = json.loads(path.read_text())
    except Exception as exc:
        return {"_missing": False, "_path": str(path), "_error": f"{type(exc).__name__}: {exc}"}
    return payload if isinstance(payload, dict) else {"_path": str(path), "_error": "report is not a JSON object"}


def report_all_pass(payload: Dict[str, Any]) -> bool:
    results = payload.get("results")
    return isinstance(results, list) and bool(results) and all(
        isinstance(row, dict) and row.get("status") == "pass"
        for row in results
    )


def result_count(payload: Dict[str, Any]) -> int:
    results = payload.get("results")
    return len(results) if isinstance(results, list) else 0


def build_report(*, write_dependencies: bool = True) -> Dict[str, Any]:
    no_write = [] if write_dependencies else ["--no-write"]
    checks = [
        run_command("setup_no_smoke", [sys.executable, "setup_oauth.py", "--no-smoke"]),
        run_command("environment_probe", [sys.executable, "src/environment_probe.py", *no_write]),
        run_command("offline_router_smoke", [sys.executable, "src/run_router_offline_smoke.py", *no_write]),
        run_command("route_manifest", [sys.executable, "src/verify_route_manifest.py"]),
        run_command("status_report", [sys.executable, "src/status_report.py", "--no-refresh-env", *no_write]),
        run_command("readiness_report", [sys.executable, "src/readiness_report.py", *no_write]),
        run_command("git_diff_check", ["git", "diff", "--check"]),
    ]

    environment = load_json("environment_latest.json")
    readiness = load_json("readiness_latest.json")
    status = load_json("status_latest.json")
    offline = load_json("router_offline_smoke_latest.json")
    fallback = global_fallback_state()

    env_model = environment.get("codex_model_discovery") if isinstance(environment.get("codex_model_discovery"), dict) else {}
    env_bind = environment.get("localhost_bind") if isinstance(environment.get("localhost_bind"), dict) else {}
    package_health_ok = all(check["status"] == "pass" for check in checks)
    local_router_ok = report_all_pass(offline)
    live_environment_ok = env_model.get("ok") is True and env_bind.get("ok") is True
    full_goal_complete = readiness.get("goal_complete") is True
    category_counts = (
        (readiness.get("surface_audit") or {}).get("category_counts")
        if isinstance(readiness.get("surface_audit"), dict)
        else {}
    )
    if not isinstance(category_counts, dict):
        category_counts = {}
    api_key_required = int(category_counts.get("api_key_or_admin_key_required", 0) or 0)

    warnings = []
    if not full_goal_complete:
        warnings.append("Full goal is not complete in this environment.")
    if api_key_required:
        warnings.append(f"{api_key_required} OpenAI API paths still require explicit Platform/Admin credentials.")
    if env_model.get("ok") is not True:
        warnings.append("Current environment cannot reach Codex model discovery.")
    if env_bind.get("ok") is not True:
        warnings.append("Current environment cannot bind localhost for live HTTP/SDK smoke.")

    next_actions = []
    if not package_health_ok:
        next_actions.append("Fix failing doctor checks before publishing or asking users to run the bridge.")
    if env_bind.get("ok") is not True:
        next_actions.append("Run python bridge.py live-check from a normal local shell that can bind localhost.")
    if env_model.get("ok") is not True:
        next_actions.append("Run from an environment with network access before relying on model-backed calls.")
    next_actions.extend([
        "Use python bridge.py migrate path/to/app --fail-on-boundary before switching an app to the bridge.",
    ])
    if api_key_required:
        next_actions.append("Use official Platform credentials for API/Admin-key boundary paths.")

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "package_health_ok": package_health_ok,
        "local_router_ok": local_router_ok,
        "live_environment_ok": live_environment_ok,
        "full_goal_complete": full_goal_complete,
        "default_exit_ok": package_health_ok,
        "strict_exit_ok": package_health_ok and live_environment_ok and full_goal_complete,
        "bottom_line": (
            "Package health checks pass, but the current environment cannot prove the full goal."
            if package_health_ok and not full_goal_complete and not api_key_required
            else "Package health checks pass, but the full OpenAI API OAuth goal is not complete."
            if package_health_ok and not full_goal_complete
            else "Package health checks pass and the full goal is complete."
            if package_health_ok
            else "Package health checks failed."
        ),
        "coverage": {
            "official_paths": (readiness.get("surface_audit") or {}).get("official_paths_count") if isinstance(readiness.get("surface_audit"), dict) else None,
            "category_counts": (readiness.get("surface_audit") or {}).get("category_counts") if isinstance(readiness.get("surface_audit"), dict) else {},
        },
        "environment": {
            "codex_model_discovery_ok": env_model.get("ok"),
            "localhost_bind_ok": env_bind.get("ok"),
            "model_error": env_model.get("error"),
            "localhost_error": env_bind.get("error"),
        },
        "smoke": {
            "offline_results": result_count(offline),
            "offline_all_pass": local_router_ok,
        },
        "status": {
            "base_url": status.get("base_url"),
            "placeholder_api_key": status.get("placeholder_api_key"),
        },
        "platform_fallback": fallback,
        "warnings": warnings,
        "next_actions": next_actions,
        "checks": checks,
    }
    return payload


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "doctor_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    lines = [
        "# OAuth Bridge Doctor",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Package health OK: `{payload['package_health_ok']}`",
        f"- Local router OK: `{payload['local_router_ok']}`",
        f"- Live environment OK: `{payload['live_environment_ok']}`",
        f"- Full goal complete: `{payload['full_goal_complete']}`",
        f"- Platform fallback enabled: `{payload['platform_fallback']['enabled']}`",
        f"- Bottom line: {payload['bottom_line']}",
        "",
        "## Coverage",
        "",
        f"- Official paths: `{payload['coverage'].get('official_paths')}`",
        "",
        "| Category | Paths |",
        "|---|---:|",
    ]
    for category, count in sorted((payload["coverage"].get("category_counts") or {}).items()):
        lines.append(f"| `{category}` | {count} |")
    lines.extend([
        "",
        "## Environment",
        "",
        "| Check | OK | Error |",
        "|---|---|---|",
        f"| Codex model discovery | `{payload['environment'].get('codex_model_discovery_ok')}` | `{payload['environment'].get('model_error')}` |",
        f"| Localhost bind | `{payload['environment'].get('localhost_bind_ok')}` | `{payload['environment'].get('localhost_error')}` |",
        "",
        "## Platform Fallback",
        "",
        "| Check | Value |",
        "|---|---|",
        f"| Enabled | `{payload['platform_fallback'].get('enabled')}` |",
        f"| Mode | `{payload['platform_fallback'].get('mode')}` |",
        f"| API key present | `{payload['platform_fallback'].get('api_key_present')}` |",
        f"| Access token present | `{payload['platform_fallback'].get('access_token_present')}` |",
        f"| Admin key present | `{payload['platform_fallback'].get('admin_key_present')}` |",
        "",
        "## Checks",
        "",
        "| Status | Check | Return Code |",
        "|---|---|---:|",
    ])
    for check in payload["checks"]:
        lines.append(f"| `{check['status']}` | `{check['name']}` | {check['returncode']} |")
    if payload["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in payload["warnings"]:
            lines.append(f"- {warning}")
    lines.extend(["", "## Next Actions", ""])
    for action in payload["next_actions"]:
        lines.append(f"- {action}")
    lines.append("")
    (REPORTS / "doctor_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any], *, strict: bool = False) -> None:
    if strict:
        label = "strict-pass" if payload["strict_exit_ok"] else "strict-fail"
    else:
        label = "package-pass" if payload["package_health_ok"] else "package-fail"
    print("OAuth bridge doctor:", label)
    print(payload["bottom_line"])
    print()
    print(
        "state="
        f"package_health_ok={payload['package_health_ok']}; "
        f"local_router_ok={payload['local_router_ok']}; "
        f"live_environment_ok={payload['live_environment_ok']}; "
        f"full_goal_complete={payload['full_goal_complete']}"
    )
    counts = payload["coverage"].get("category_counts") or {}
    print(
        "coverage="
        f"official_paths={payload['coverage'].get('official_paths')}; "
        f"direct_oauth={counts.get('direct_official_oauth_verified', 0)}; "
        f"local_bridge={counts.get('local_compat_or_chatgpt_backend_bridge', 0)}; "
        f"platform_boundary={counts.get('api_key_or_admin_key_required', 0)}"
    )
    print(
        "environment="
        f"codex_model_discovery_ok={payload['environment'].get('codex_model_discovery_ok')}; "
        f"localhost_bind_ok={payload['environment'].get('localhost_bind_ok')}"
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
    if payload["warnings"]:
        print()
        print("Warnings:")
        for warning in payload["warnings"]:
            print(f"- {warning}")
    print()
    print("Next actions:")
    for action in payload["next_actions"][:5]:
        print(f"- {action}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a user-facing OAuth bridge doctor check.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/doctor_latest.*.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero unless package health, live environment, and full-goal readiness all pass.",
    )
    args = parser.parse_args()

    payload = build_report(write_dependencies=not args.no_write)
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload, strict=args.strict)
    ok_key = "strict_exit_ok" if args.strict else "default_exit_ok"
    return 0 if payload.get(ok_key) is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
