from __future__ import annotations

import argparse
import json
import shlex
import time
from pathlib import Path
from typing import Any, Dict, List

from check_openai_usage import build_report as build_usage_report
from generate_client_config import build_report as build_client_config_report
from platform_fallback import API_KEY_ENV, ENABLE_ENV, MODE_ENV


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

READY_CATEGORIES = {
    "direct_official_oauth_verified",
    "local_compat_or_chatgpt_backend_bridge",
}

BOUNDARY_CATEGORIES = {
    "api_key_or_admin_key_required",
    "resource_bound_not_fully_verified",
    "official_route_auth_reached_but_not_complete",
    "not_available_current_deployment",
    "not_probed_directly",
    "not_in_surface_audit",
    "read_error",
}


def shell_join(parts: List[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def compact_finding(finding: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": finding.get("source"),
        "line": finding.get("line"),
        "kind": finding.get("kind"),
        "token": finding.get("token"),
        "normalized_path": finding.get("normalized_path"),
        "matched_path": finding.get("matched_path"),
        "match_type": finding.get("match_type"),
        "category": finding.get("category"),
        "decision": finding.get("decision"),
        "action": finding.get("action"),
        "evidence": finding.get("evidence"),
        "sdk_api_path": finding.get("sdk_api_path"),
    }


def build_report(
    items: List[str],
    *,
    host: str,
    port: int,
    base_url: str | None,
) -> Dict[str, Any]:
    usage = build_usage_report(items)
    client_config = build_client_config_report(host=host, port=port, base_url=base_url)
    findings = [finding for finding in usage.get("findings", []) if isinstance(finding, dict)]
    ready = [compact_finding(finding) for finding in findings if finding.get("category") in READY_CATEGORIES]
    boundary = [compact_finding(finding) for finding in findings if finding.get("category") in BOUNDARY_CATEGORIES]
    other = [
        compact_finding(finding)
        for finding in findings
        if finding.get("category") not in READY_CATEGORIES and finding.get("category") not in BOUNDARY_CATEGORIES
    ]

    quoted_items = [str(item) for item in items]
    gate_command = shell_join(["python", "bridge.py", "check", *quoted_items, "--fail-on-boundary"])
    migrate_command = shell_join(["python", "bridge.py", "migrate", *quoted_items])
    start_proxy = str((client_config.get("commands") or {}).get("start_proxy") or f"python bridge.py serve --host {host} --port {port}")
    resolved_base_url = str(client_config.get("base_url"))
    placeholder_key = str(client_config.get("placeholder_api_key"))

    if not findings:
        decision = "no_openai_usage_found"
        bottom_line = "No OpenAI REST paths or known SDK calls were found in the supplied input."
    elif boundary:
        decision = "needs_changes_before_local_bridge"
        bottom_line = (
            "Not ready for OAuth-only migration: one or more OpenAI calls still need a Platform/Admin credential, "
            "live resource proof, or a disabled fallback."
        )
    else:
        decision = "ready_to_try_local_bridge"
        bottom_line = (
            "Ready to try the local OAuth bridge for the detected OpenAI calls. Run live smoke from a normal shell "
            "before treating this as production-ready."
        )

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "inputs": quoted_items,
        "decision": decision,
        "bottom_line": bottom_line,
        "base_url": resolved_base_url,
        "placeholder_api_key": placeholder_key,
        "summary": {
            "findings": usage.get("finding_count"),
            "usable_without_platform_key": usage.get("usable_without_platform_key_count"),
            "blocked_or_unproven": usage.get("blocked_or_unproven_count"),
            "category_counts": usage.get("category_counts"),
        },
        "commands": {
            "start_proxy": start_proxy,
            "set_env": f"export OPENAI_BASE_URL={resolved_base_url} OPENAI_API_KEY={placeholder_key}",
            "ci_gate": gate_command,
            "refresh_plan": migrate_command,
            "status": "python bridge.py status",
            "readiness": "python bridge.py readiness",
            "enable_boundary_fallback": f"export {ENABLE_ENV}=1 {MODE_ENV}=boundary {API_KEY_ENV}=sk-...",
            "enable_prefer_platform": f"export {ENABLE_ENV}=1 {MODE_ENV}=prefer {API_KEY_ENV}=sk-...",
        },
        "steps": [
            "Resolve every blocked_or_unproven finding before claiming an OAuth-only migration.",
            "Start the bridge in a normal local shell that can bind localhost.",
            "Point the app SDK/client to OPENAI_BASE_URL and the placeholder OPENAI_API_KEY below.",
            "For a hybrid migration, use boundary fallback for blocked routes; use prefer mode only when hosted OpenAI API behavior should override local compatibility handlers.",
            "Run the app's own tests plus bridge.py smoke or bridge.py sdk-smoke from a non-sandboxed shell.",
            "Add the ci_gate command to prevent Platform-only routes from slipping back in.",
        ],
        "ready_findings": ready,
        "boundary_findings": boundary,
        "other_findings": other,
    }


def md_escape(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|")


def location(finding: Dict[str, Any]) -> str:
    source = str(finding.get("source") or "")
    line = finding.get("line")
    return f"{source}:{line}" if line is not None else source


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "migration_plan_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))

    lines = [
        "# OAuth Bridge Migration Plan",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Decision: `{payload['decision']}`",
        f"- Bottom line: {payload['bottom_line']}",
        f"- Inputs: `{', '.join(payload['inputs'])}`",
        f"- Base URL: `{payload['base_url']}`",
        f"- Placeholder API key: `{payload['placeholder_api_key']}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Findings | {payload['summary'].get('findings')} |",
        f"| Usable without Platform key | {payload['summary'].get('usable_without_platform_key')} |",
        f"| Blocked or unproven | {payload['summary'].get('blocked_or_unproven')} |",
        "",
        "## Commands",
        "",
        "```bash",
        payload["commands"]["start_proxy"],
        payload["commands"]["set_env"],
        payload["commands"]["ci_gate"],
        "# optional hybrid Platform fallback:",
        payload["commands"]["enable_boundary_fallback"],
        "# optional exact hosted API preference:",
        payload["commands"]["enable_prefer_platform"],
        "```",
        "",
        "## Steps",
        "",
    ]
    for step in payload["steps"]:
        lines.append(f"- {step}")

    for title, key in [
        ("Ready Findings", "ready_findings"),
        ("Blocked Or Unproven Findings", "boundary_findings"),
        ("Other Findings", "other_findings"),
    ]:
        rows = payload.get(key) or []
        lines.extend([
            "",
            f"## {title}",
            "",
        ])
        if not rows:
            lines.append("- None")
            continue
        lines.extend([
            "| Location | Token | Path | Matched Path | Category | Action | Evidence |",
            "|---|---|---|---|---|---|---|",
        ])
        for finding in rows:
            lines.append(
                "| "
                f"`{md_escape(location(finding))}` | "
                f"`{md_escape(finding.get('token'))}` | "
                f"`{md_escape(finding.get('normalized_path'))}` | "
                f"`{md_escape(finding.get('matched_path'))}` | "
                f"`{md_escape(finding.get('category'))}` | "
                f"{md_escape(finding.get('action'))} | "
                f"`{md_escape(finding.get('evidence'))}` |"
            )
    lines.append("")
    (REPORTS / "migration_plan_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any], *, limit: int) -> None:
    print("OAuth bridge migration plan:", payload["decision"])
    print(payload["bottom_line"])
    print()
    print(f"base_url={payload['base_url']}")
    print(f"placeholder_api_key={payload['placeholder_api_key']}")
    print(
        "summary="
        f"findings={payload['summary'].get('findings')}; "
        f"usable_without_platform_key={payload['summary'].get('usable_without_platform_key')}; "
        f"blocked_or_unproven={payload['summary'].get('blocked_or_unproven')}"
    )
    print()
    print("Commands:")
    print(f"  {payload['commands']['start_proxy']}")
    print(f"  {payload['commands']['set_env']}")
    print(f"  {payload['commands']['ci_gate']}")
    blocked = payload.get("boundary_findings") or []
    if blocked:
        print()
        print("Blocked or unproven:")
        for finding in blocked[:limit]:
            matched_path = finding.get("matched_path")
            path = finding.get("normalized_path")
            match_note = f" (matches {matched_path})" if matched_path and matched_path != path else ""
            print(
                f"- {location(finding)}: {finding.get('token')} -> "
                f"{path}{match_note} [{finding.get('category')}]"
            )
            print(f"  {finding.get('action')}")
        remaining = len(blocked) - min(limit, len(blocked))
        if remaining > 0:
            print(f"... {remaining} more in reports/migration_plan_latest.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an app migration plan for the local OAuth bridge.")
    parser.add_argument("items", nargs="+", help="OpenAI API paths, full URLs, files, or directories to scan.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--base-url", help="Override the generated local bridge base URL.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--limit", type=int, default=20, help="Number of blocked findings to print.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/migration_plan_latest.*.")
    parser.add_argument("--fail-on-boundary", action="store_true", help="Exit non-zero when blocked or unproven paths are found.")
    args = parser.parse_args()

    payload = build_report(args.items, host=args.host, port=args.port, base_url=args.base_url)
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload, limit=max(args.limit, 0))
    if args.fail_on_boundary and payload["summary"].get("blocked_or_unproven"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
