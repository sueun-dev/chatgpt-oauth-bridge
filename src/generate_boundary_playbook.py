from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from generate_coverage_map import BLOCKED_CATEGORIES, READY_CATEGORIES, product_group
from platform_fallback import (
    ACCESS_TOKEN_ENV,
    ADMIN_KEY_ENV,
    API_KEY_ENV,
    ENABLE_ENV,
    credential_envs_for_path,
)
from surface_audit import load_surface_payload


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def load_surface() -> Dict[str, Any]:
    return load_surface_payload()


def compact_path(row: Dict[str, Any]) -> Dict[str, Any]:
    path = str(row.get("path") or "")
    return {
        "path": path,
        "category": row.get("category"),
        "credential_envs": credential_envs_for_path(path),
        "support": row.get("support"),
        "evidence": row.get("evidence"),
    }


def group_policy(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = Counter(str(row.get("category") or "not_probed_directly") for row in rows)
    ready_rows = [row for row in rows if row.get("category") in READY_CATEGORIES]
    blocked_rows = [row for row in rows if row.get("category") in BLOCKED_CATEGORIES]
    direct_rows = [row for row in rows if row.get("category") == "direct_official_oauth_verified"]
    local_rows = [row for row in rows if row.get("category") == "local_compat_or_chatgpt_backend_bridge"]
    credential_envs = sorted({
        env
        for row in blocked_rows
        for env in credential_envs_for_path(str(row.get("path") or ""))
    })
    if not blocked_rows:
        mode = "oauth_or_local_only"
        action = "Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof."
    elif ready_rows:
        mode = "split"
        action = "Use the ready paths through the local bridge and keep the blocked paths on explicit Platform/Admin fallback or disabled."
    else:
        mode = "platform_or_disabled"
        action = "Do not expose this group as OAuth-only. Use explicit Platform/Admin fallback credentials or disable it."
    return {
        "mode": mode,
        "action": action,
        "total_paths": len(rows),
        "ready_paths": len(ready_rows),
        "direct_hosted_oauth_paths": len(direct_rows),
        "local_bridge_paths": len(local_rows),
        "blocked_or_unproven_paths": len(blocked_rows),
        "category_counts": dict(sorted(counts.items())),
        "credential_envs": credential_envs,
        "ready_examples": [compact_path(row) for row in ready_rows[:8]],
        "blocked_examples": [compact_path(row) for row in blocked_rows[:12]],
    }


def build_report() -> Dict[str, Any]:
    surface = load_surface()
    rows = [row for row in surface.get("rows", []) if isinstance(row, dict)]
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[product_group(str(row.get("path") or ""))].append(row)

    groups = []
    for name in sorted(grouped):
        group_rows = sorted(grouped[name], key=lambda row: str(row.get("path") or ""))
        groups.append({"group": name, **group_policy(group_rows)})

    boundary_groups = [group for group in groups if group["blocked_or_unproven_paths"]]
    platform_paths = [
        compact_path(row)
        for row in rows
        if row.get("category") in BLOCKED_CATEGORIES
    ]
    credential_counts = Counter(
        env
        for row in platform_paths
        for env in row.get("credential_envs", [])
    )
    ready_total = sum(group["ready_paths"] for group in groups)
    direct_total = sum(group["direct_hosted_oauth_paths"] for group in groups)
    local_total = sum(group["local_bridge_paths"] for group in groups)
    blocked_total = sum(group["blocked_or_unproven_paths"] for group in groups)
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "object": "oauth_compat.boundary_playbook",
        "goal_complete": blocked_total == 0,
        "boundary_map_complete": blocked_total == 0,
        "hosted_oauth_complete": direct_total == len(rows),
        "bottom_line": (
            "Not complete: remaining groups need explicit Platform/Admin fallback, live resource proof, or disabled features."
            if blocked_total
            else (
                "No blocked path remains in the local bridge map, but hosted OpenAI OAuth is directly verified "
                f"for {direct_total} paths; {local_total} paths are local or ChatGPT-backend compatibility."
            )
        ),
        "source": {
            "openapi_source": surface.get("openapi_source"),
            "source_warning": surface.get("source_warning"),
            "surface_generated_at": surface.get("generated_at"),
            "official_paths_count": surface.get("official_paths_count"),
        },
        "summary": {
            "ready_paths": ready_total,
            "direct_hosted_oauth_paths": direct_total,
            "local_bridge_paths": local_total,
            "blocked_or_unproven_paths": blocked_total,
            "boundary_groups": len(boundary_groups),
            "credential_env_counts": dict(sorted(credential_counts.items())),
        },
        "commands": {
            "strict_oauth_gate": "python bridge.py check path/to/your/app --fail-on-boundary",
            "migration_plan": "python bridge.py migrate path/to/your/app --fail-on-boundary",
            "status": "python bridge.py status",
            "coverage": "python bridge.py coverage",
            "enable_platform_fallback": f"export {ENABLE_ENV}=1",
            "platform_api_key": f"export {API_KEY_ENV}=sk-...",
            "official_access_token": f"export {ACCESS_TOKEN_ENV}=official-workload-identity-bearer",
            "admin_key": f"export {ADMIN_KEY_ENV}=sk-admin-or-ek-...",
        },
        "warnings": [
            "Platform fallback is hybrid routing, not ChatGPT/Codex OAuth support.",
            "OPENAI_ACCESS_TOKEN is for official OpenAI workload-identity-style bearer tokens, not the local ChatGPT/Codex OAuth token.",
            "Admin/project/org paths should use a separate Admin credential and should not be enabled by accident in user apps.",
            "Resource-bound Realtime paths still need live call IDs before they can be marked complete.",
        ],
        "groups": groups,
        "platform_or_unfinished_paths": platform_paths,
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "boundary_playbook_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    lines = [
        "# OAuth Boundary Playbook",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Boundary map complete: `{payload['boundary_map_complete']}`",
        f"- Hosted OpenAI OAuth complete: `{payload['hosted_oauth_complete']}`",
        f"- Bottom line: {payload['bottom_line']}",
        f"- Official paths: `{payload['source'].get('official_paths_count')}`",
        f"- Ready paths: `{payload['summary'].get('ready_paths')}`",
        f"- Direct hosted OAuth paths: `{payload['summary'].get('direct_hosted_oauth_paths')}`",
        f"- Local bridge paths: `{payload['summary'].get('local_bridge_paths')}`",
        f"- Blocked or unproven paths: `{payload['summary'].get('blocked_or_unproven_paths')}`",
    ]
    if payload["source"].get("source_warning"):
        lines.append(f"- Source warning: {payload['source']['source_warning']}")
    lines.extend([
        "",
        "## Safe Modes",
        "",
        "- OAuth-only mode: run the strict gate and disable every blocked route.",
        "- Hybrid mode: enable Platform fallback explicitly and provide the right official credential for each boundary route.",
        "- Admin mode: keep org/project/admin paths behind a separate Admin credential and explicit app feature flag.",
        "",
        "## Commands",
        "",
        "```bash",
    ])
    for command in payload["commands"].values():
        lines.append(command)
    lines.extend([
        "```",
        "",
        "## Groups",
        "",
        "| Group | Mode | Direct OAuth | Local Bridge | Blocked/Unproven | Credential Envs | Action |",
        "|---|---|---:|---:|---:|---|---|",
    ])
    for group in payload["groups"]:
        envs = ", ".join(group.get("credential_envs") or [])
        action = str(group.get("action") or "").replace("|", "\\|")
        lines.append(
            f"| `{group['group']}` | `{group['mode']}` | {group['direct_hosted_oauth_paths']} | "
            f"{group['local_bridge_paths']} | "
            f"{group['blocked_or_unproven_paths']} | `{envs}` | {action} |"
        )
    lines.extend(["", "## Blocked Or Unproven Paths", ""])
    for row in payload["platform_or_unfinished_paths"]:
        envs = ", ".join(row.get("credential_envs") or [])
        support = str(row.get("support") or "").replace("|", "\\|")
        lines.append(f"- `{row['path']}`: `{row['category']}`; envs=`{envs}`; {support}")
    lines.extend(["", "## Warnings", ""])
    for warning in payload["warnings"]:
        lines.append(f"- {warning}")
    lines.append("")
    (REPORTS / "boundary_playbook_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any], *, limit: int) -> None:
    print("OAuth boundary playbook:", "complete" if payload["goal_complete"] else "not complete")
    print(payload["bottom_line"])
    print(
        "summary="
        f"ready_paths={payload['summary']['ready_paths']}; "
        f"direct_hosted_oauth_paths={payload['summary']['direct_hosted_oauth_paths']}; "
        f"local_bridge_paths={payload['summary']['local_bridge_paths']}; "
        f"blocked_or_unproven_paths={payload['summary']['blocked_or_unproven_paths']}; "
        f"boundary_groups={payload['summary']['boundary_groups']}"
    )
    print()
    print("Commands:")
    for name, command in payload["commands"].items():
        print(f"- {name}: {command}")
    blocked_groups = [group for group in payload["groups"] if group["blocked_or_unproven_paths"]]
    if blocked_groups:
        print()
        print("Boundary groups:")
        for group in blocked_groups[:limit]:
            envs = ",".join(group.get("credential_envs") or [])
            print(
                f"- {group['group']}: {group['mode']} "
                f"ready={group['ready_paths']} blocked={group['blocked_or_unproven_paths']} envs={envs}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a safe playbook for remaining OAuth bridge boundaries.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--limit", type=int, default=20, help="Number of boundary groups to print.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/boundary_playbook_latest.*.")
    args = parser.parse_args()

    payload = build_report()
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload, limit=max(args.limit, 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
