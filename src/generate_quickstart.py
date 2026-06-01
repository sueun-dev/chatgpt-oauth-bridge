from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from generate_client_config import build_report as build_client_config_report
from generate_client_config import write_reports as write_client_config_reports
from generate_boundary_playbook import build_report as build_boundary_playbook_report
from generate_boundary_playbook import write_reports as write_boundary_playbook_reports
from generate_route_policy import build_report as build_route_policy_report
from generate_route_policy import write_reports as write_route_policy_reports
from goal_audit_report import build_report as build_goal_audit_report
from goal_audit_report import write_reports as write_goal_audit_reports
from publish_check import build_report as build_publish_check_report
from publish_check import write_reports as write_publish_check_reports
from readiness_report import build_report as build_readiness_report


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def build_report(
    *,
    host: str,
    port: int,
    base_url: Optional[str],
) -> Dict[str, Any]:
    client_config = build_client_config_report(host=host, port=port, base_url=base_url)
    route_policy = build_route_policy_report()
    goal_audit = build_goal_audit_report()
    readiness = build_readiness_report()
    publish = build_publish_check_report()
    counts = goal_audit.get("counts") if isinstance(goal_audit.get("counts"), dict) else {}
    summary = route_policy.get("summary") if isinstance(route_policy.get("summary"), dict) else {}
    branch = publish.get("branch") if isinstance(publish.get("branch"), dict) else {}
    generated_files = client_config.get("generated_files") if isinstance(client_config.get("generated_files"), dict) else {}
    why_not_complete = []
    api_key_boundaries = int(counts.get("api_key_or_admin_key_required", 0) or 0)
    if api_key_boundaries:
        why_not_complete.append(f"{api_key_boundaries} documented paths remain API/Admin-key boundaries.")
    why_not_complete.append("The current environment cannot verify live model discovery or localhost HTTP/SDK smoke.")
    unfinished = int(counts.get("unfinished_or_resource_bound", 0) or 0)
    if unfinished:
        why_not_complete.insert(1, f"{unfinished} documented paths still need live resource proof or remain incomplete.")
    if publish.get("publish_ready") is not True:
        why_not_complete.append(
            "GitHub publish state is not ready: "
            f"local HEAD does not match {branch.get('upstream') or 'the configured upstream'}."
        )

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "object": "oauth_compat.quickstart",
        "goal_complete": goal_audit.get("goal_complete") is True and readiness.get("goal_complete") is True,
        "bottom_line": goal_audit.get("bottom_line") or readiness.get("bottom_line"),
        "base_url": client_config.get("base_url"),
        "placeholder_api_key": client_config.get("placeholder_api_key"),
        "counts": counts,
        "route_policy_summary": summary,
        "publish_state": {
            "publish_ready": publish.get("publish_ready"),
            "local_tree_ready": publish.get("local_tree_ready"),
            "branch": branch,
            "counts": publish.get("counts"),
        },
        "generated_files": {
            "quickstart": "reports/quickstart_latest.md",
            "client_config": "reports/client_config_latest.md",
            "env_example": generated_files.get("env_example", "reports/openai_bridge.env.example"),
            "ci_gate": generated_files.get("ci_gate", "reports/openai_bridge_ci_gate.sh"),
            "launch_gate": generated_files.get("launch_gate", "reports/openai_bridge_launch_gate.sh"),
            "publish_gate": generated_files.get("publish_gate", "reports/openai_bridge_publish_gate.sh"),
            "finish_gate": generated_files.get("finish_gate", "reports/openai_bridge_finish_gate.sh"),
            "route_policy": "reports/openai_bridge_route_policy.md",
            "route_policy_json": "reports/openai_bridge_route_policy.json",
            "route_policy_csv": "reports/openai_bridge_route_policy.csv",
            "goal_audit": "reports/goal_audit_latest.md",
            "publish_check": "reports/publish_check_latest.md",
            "boundary_playbook": "reports/boundary_playbook_latest.md",
        },
        "commands": {
            "setup": "python bridge.py setup",
            "start_proxy": (client_config.get("commands") or {}).get("start_proxy"),
            "source_env": "set -a; source reports/openai_bridge.env.example; set +a",
            "status": "python bridge.py status",
            "verdict": "python bridge.py verdict",
            "strict_verdict": "python bridge.py verdict --strict",
            "policy": "python bridge.py policy",
            "check_app": "python bridge.py check path/to/your/app --fail-on-boundary",
            "migrate_app": "python bridge.py migrate path/to/your/app --fail-on-boundary",
            "ci_gate": "bash reports/openai_bridge_ci_gate.sh path/to/your/app",
            "preflight": "python bridge.py preflight",
            "live_check": "python bridge.py live-check",
            "publish_check": "python bridge.py publish-check",
            "publish_gate": "bash reports/openai_bridge_publish_gate.sh --push",
            "finish": "python bridge.py finish --push",
            "finish_gate": "bash reports/openai_bridge_finish_gate.sh --push",
            "strict_doctor": "python bridge.py doctor --strict",
        },
        "steps": [
            {
                "name": "Confirm local OAuth source",
                "command": "python bridge.py setup",
                "expected": "OAuth source is present. If live model calls are unavailable, setup prints the missing network/token condition.",
            },
            {
                "name": "Generate client files and route policy",
                "command": "python bridge.py quickstart",
                "expected": "Writes env, CI gate, launch gate, quickstart, route policy, and goal audit reports.",
            },
            {
                "name": "Start the local OpenAI-shaped proxy",
                "command": (client_config.get("commands") or {}).get("start_proxy"),
                "expected": "Runs the local /v1 proxy when localhost binding is allowed.",
            },
            {
                "name": "Point SDK clients at the bridge",
                "command": "set -a; source reports/openai_bridge.env.example; set +a",
                "expected": "OPENAI_BASE_URL points at the local bridge and OPENAI_API_KEY is the placeholder SDK value.",
            },
            {
                "name": "Scan the app before migration",
                "command": "python bridge.py migrate path/to/your/app --fail-on-boundary",
                "expected": "Ready paths and any blocked/API-key boundary paths are separated before traffic moves.",
            },
            {
                "name": "Keep the boundary gate in CI",
                "command": "bash reports/openai_bridge_ci_gate.sh path/to/your/app",
                "expected": "Fails when Platform-only routes are introduced into an OAuth-only app.",
            },
            {
                "name": "Prove live launch readiness",
                "command": "bash reports/openai_bridge_launch_gate.sh",
                "expected": "Runs environment, HTTP proxy smoke, SDK smoke, readiness, and strict doctor checks in one gate.",
            },
            {
                "name": "Check GitHub publish state",
                "command": "bash reports/openai_bridge_publish_gate.sh --push",
                "expected": "Runs preflight, pushes the current branch, then fails unless local HEAD matches the configured upstream branch.",
            },
            {
                "name": "Finish publish and launch in one gate",
                "command": "python bridge.py finish --push",
                "expected": "Runs the publish gate first, then the live launch gate. It fails until GitHub, network, and localhost evidence all pass.",
            },
            {
                "name": "Fail automation when the full goal is incomplete",
                "command": "python bridge.py verdict --strict",
                "expected": "Exits non-zero until the full-goal verdict is complete.",
            },
        ],
        "oauth_only_rules": [
            f"Strict hosted OAuth mode allows exactly {summary.get('allow_oauth_only')} documented paths.",
            f"Local bridge mode allows {summary.get('allow_local_bridge')} documented paths through direct OAuth or local compatibility.",
            f"Local bridge mode blocks {summary.get('deny_local_bridge')} documented paths when the route policy reports a Platform/Admin boundary or missing live resource proof.",
            "Do not treat local compatibility routes as hosted OpenAI Platform OAuth proof.",
            "Do not use the placeholder oauth-local-proxy value as a Platform API credential.",
        ],
        "fallback_rules": [
            "Fallback is disabled by default.",
            "Set OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1 only when the app intentionally uses official Platform/Admin credentials.",
            "Use OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=boundary for boundary-only forwarding.",
            "Use OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=prefer only when exact hosted OpenAI API behavior should override local compatibility.",
        ],
        "why_not_complete": why_not_complete,
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    client_config = build_client_config_report(base_url=str(payload.get("base_url") or ""))
    write_client_config_reports(client_config)
    write_route_policy_reports(build_route_policy_report())
    write_boundary_playbook_reports(build_boundary_playbook_report())
    write_goal_audit_reports(build_goal_audit_report())
    write_publish_check_reports(build_publish_check_report())

    (REPORTS / "quickstart_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    lines = [
        "# OAuth Bridge Quickstart",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Goal complete: `{payload['goal_complete']}`",
        f"- Bottom line: {payload['bottom_line']}",
        f"- Base URL: `{payload['base_url']}`",
        f"- Placeholder API key: `{payload['placeholder_api_key']}`",
        "",
        "## Current Counts",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ]
    for key, value in payload["counts"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend([
        "",
        "## Route Policy",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ])
    for key, value in payload["route_policy_summary"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend([
        "",
        "## Publish State",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Publish ready | `{payload['publish_state'].get('publish_ready')}` |",
        f"| Local tree ready | `{payload['publish_state'].get('local_tree_ready')}` |",
        f"| Branch | `{(payload['publish_state'].get('branch') or {}).get('branch')}` |",
        f"| Upstream | `{(payload['publish_state'].get('branch') or {}).get('upstream')}` |",
        f"| Head matches upstream | `{(payload['publish_state'].get('branch') or {}).get('head_matches_upstream')}` |",
    ])
    lines.extend([
        "",
        "## First Run",
        "",
        "```bash",
        payload["commands"]["setup"],
        "python bridge.py quickstart",
        "bash reports/openai_bridge_launch_gate.sh",
        payload["commands"]["start_proxy"] or "python bridge.py serve --host 127.0.0.1 --port 8787",
        "```",
        "",
        "## App Environment",
        "",
        "```bash",
        payload["commands"]["source_env"],
        "```",
        "",
        "## Scan Before Migrating",
        "",
        "```bash",
        payload["commands"]["migrate_app"],
        payload["commands"]["ci_gate"],
        "```",
        "",
        "## Check Before Publishing",
        "",
        "```bash",
        payload["commands"]["publish_gate"],
        payload["commands"]["finish"],
        "```",
        "",
        "## Steps",
        "",
    ])
    for step in payload["steps"]:
        lines.append(f"- `{step['command']}`: {step['expected']}")
    lines.extend(["", "## OAuth-Only Rules", ""])
    for item in payload["oauth_only_rules"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Fallback Rules", ""])
    for item in payload["fallback_rules"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Why This Is Not Complete Yet", ""])
    for item in payload["why_not_complete"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Generated Files", ""])
    for name, path in payload["generated_files"].items():
        lines.append(f"- `{name}`: `{path}`")
    lines.append("")
    (REPORTS / "quickstart_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any]) -> None:
    print("OAuth bridge quickstart:", "complete" if payload["goal_complete"] else "not complete")
    print(payload["bottom_line"])
    print()
    print(f"base_url={payload['base_url']}")
    print(f"placeholder_api_key={payload['placeholder_api_key']}")
    counts = payload["counts"]
    policy = payload["route_policy_summary"]
    publish = payload["publish_state"]
    branch = publish.get("branch") or {}
    print(
        "coverage="
        f"official_paths={counts.get('official_paths')}; "
        f"direct_oauth={counts.get('direct_official_oauth_verified')}; "
        f"local_bridge={counts.get('local_compat_or_chatgpt_backend_bridge')}; "
        f"hosted_oauth_allow={policy.get('allow_oauth_only')}; "
        f"local_bridge_allow={policy.get('allow_local_bridge')}; "
        f"local_bridge_deny={policy.get('deny_local_bridge')}"
    )
    print(
        "publish="
        f"ready={publish.get('publish_ready')}; "
        f"branch={branch.get('branch')}; "
        f"upstream={branch.get('upstream')}; "
        f"head_matches_upstream={branch.get('head_matches_upstream')}"
    )
    print()
    print("First run:")
    print(f"  {payload['commands']['setup']}")
    print("  python bridge.py quickstart")
    print("  bash reports/openai_bridge_launch_gate.sh")
    print(f"  {payload['commands']['start_proxy']}")
    print()
    print("Before migrating an app:")
    print(f"  {payload['commands']['migrate_app']}")
    print(f"  {payload['commands']['ci_gate']}")
    print()
    print("Before publishing:")
    print(f"  {payload['commands']['publish_gate']}")
    print(f"  {payload['commands']['finish']}")
    print()
    print("Generated:")
    for path in payload["generated_files"].values():
        print(f"  {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the first-run bundle for using the OAuth bridge safely.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--base-url", help="Override the generated local bridge base URL.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/quickstart_latest.*.")
    args = parser.parse_args()

    payload = build_report(host=args.host, port=args.port, base_url=args.base_url)
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
