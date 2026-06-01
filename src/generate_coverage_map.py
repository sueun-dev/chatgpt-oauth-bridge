from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from generate_compatibility_guide import CATEGORY_ACTIONS


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

READY_CATEGORIES = {
    "direct_official_oauth_verified",
    "local_compat_or_chatgpt_backend_bridge",
}

BLOCKED_CATEGORIES = {
    "api_key_or_admin_key_required",
    "resource_bound_not_fully_verified",
    "official_route_auth_reached_but_not_complete",
    "not_available_current_deployment",
    "not_probed_directly",
}


def load_surface() -> Dict[str, Any]:
    path = REPORTS / "openai_surface_audit_latest.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing surface audit report: {path}")
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid surface audit report: {path}")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError(f"Surface audit report has no rows list: {path}")
    return payload


def product_group(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    if not parts:
        return "root"
    first = parts[0]
    if first == "organization" and len(parts) > 1:
        if parts[1] == "usage":
            return "organization/usage"
        if parts[1] == "projects":
            return "organization/projects"
        return "organization/admin"
    if first == "fine_tuning":
        return "fine_tuning"
    if first == "realtime":
        return "realtime"
    if first == "vector_stores":
        return "vector_stores"
    if first == "chat":
        return "chat"
    return first


def group_decision(counts: Counter[str]) -> str:
    total = sum(counts.values())
    if total == 0:
        return "empty"
    ready = sum(counts.get(category, 0) for category in READY_CATEGORIES)
    blocked = sum(counts.get(category, 0) for category in BLOCKED_CATEGORIES)
    if ready == total:
        return "usable_without_platform_key"
    if counts.get("api_key_or_admin_key_required", 0) == total:
        return "platform_credentials_required"
    if ready and blocked:
        return "mixed"
    if blocked:
        return "blocked_or_unproven"
    return "review_required"


def group_action(decision: str) -> str:
    if decision == "usable_without_platform_key":
        return "Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof."
    if decision == "platform_credentials_required":
        return "Keep this product group on official Platform/Admin credentials or disable it for OAuth-only deployments."
    if decision == "mixed":
        return "Split features: route ready paths through the local bridge and keep boundary paths on Platform credentials or disabled."
    if decision == "blocked_or_unproven":
        return "Do not expose this group as OAuth-ready until live/resource-bound proof exists."
    return "Inspect individual paths before exposing this group."


def compact_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "path": row.get("path"),
        "category": row.get("category"),
        "support": row.get("support"),
        "evidence": row.get("evidence"),
    }


def build_report() -> Dict[str, Any]:
    surface = load_surface()
    rows = [row for row in surface.get("rows", []) if isinstance(row, dict)]
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        path = str(row.get("path") or "")
        grouped[product_group(path)].append(row)

    groups = []
    for name in sorted(grouped):
        group_rows = sorted(grouped[name], key=lambda row: str(row.get("path") or ""))
        counts = Counter(str(row.get("category") or "not_probed_directly") for row in group_rows)
        decision = group_decision(counts)
        ready_examples = [compact_row(row) for row in group_rows if row.get("category") in READY_CATEGORIES][:6]
        blocked_examples = [compact_row(row) for row in group_rows if row.get("category") in BLOCKED_CATEGORIES][:8]
        direct = counts.get("direct_official_oauth_verified", 0)
        local = counts.get("local_compat_or_chatgpt_backend_bridge", 0)
        groups.append({
            "group": name,
            "decision": decision,
            "action": group_action(decision),
            "total_paths": len(group_rows),
            "ready_paths": sum(counts.get(category, 0) for category in READY_CATEGORIES),
            "direct_hosted_oauth_paths": direct,
            "local_bridge_paths": local,
            "blocked_or_unproven_paths": sum(counts.get(category, 0) for category in BLOCKED_CATEGORIES),
            "category_counts": dict(sorted(counts.items())),
            "ready_examples": ready_examples,
            "blocked_examples": blocked_examples,
        })

    overall_counts = Counter(str(row.get("category") or "not_probed_directly") for row in rows)
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "goal_complete": all(group["decision"] == "usable_without_platform_key" for group in groups),
        "local_bridge_coverage_complete": all(group["decision"] == "usable_without_platform_key" for group in groups),
        "hosted_oauth_complete": overall_counts.get("direct_official_oauth_verified", 0) == len(rows),
        "bottom_line": (
            "Not complete: some OpenAI product groups still require Platform/Admin credentials or stronger live proof."
            if any(group["decision"] != "usable_without_platform_key" for group in groups)
            else (
                "Complete as a local bridge coverage map. This is not a hosted OpenAI Platform OAuth replacement; "
                "inspect direct_hosted_oauth_paths versus local_bridge_paths."
            )
        ),
        "source": {
            "openapi_source": surface.get("openapi_source"),
            "source_warning": surface.get("source_warning"),
            "surface_generated_at": surface.get("generated_at"),
            "official_paths_count": surface.get("official_paths_count"),
        },
        "category_counts": dict(sorted(overall_counts.items())),
        "groups": groups,
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "coverage_map_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))

    csv_lines = [
        "group,decision,total_paths,ready_paths,direct_hosted_oauth_paths,local_bridge_paths,blocked_or_unproven_paths,category_counts"
    ]
    for group in payload["groups"]:
        counts = json.dumps(group["category_counts"], sort_keys=True).replace('"', '""')
        csv_lines.append(
            f"{group['group']},{group['decision']},{group['total_paths']},"
            f"{group['ready_paths']},{group['direct_hosted_oauth_paths']},"
            f"{group['local_bridge_paths']},{group['blocked_or_unproven_paths']},\"{counts}\""
        )
    (REPORTS / "coverage_map_latest.csv").write_text("\n".join(csv_lines) + "\n")

    lines = [
        "# OpenAI OAuth Bridge Coverage Map",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Local bridge coverage complete: `{payload['local_bridge_coverage_complete']}`",
        f"- Hosted OpenAI OAuth complete: `{payload['hosted_oauth_complete']}`",
        f"- Bottom line: {payload['bottom_line']}",
        f"- Official paths: `{payload['source'].get('official_paths_count')}`",
    ]
    if payload["source"].get("source_warning"):
        lines.append(f"- Source warning: {payload['source']['source_warning']}")
    lines.extend([
        "",
        "## Product Groups",
        "",
        "| Group | Decision | Direct OAuth | Local Bridge | Blocked/Unproven | Total | Action |",
        "|---|---|---:|---:|---:|---:|---|",
    ])
    for group in payload["groups"]:
        action = str(group["action"]).replace("|", "\\|")
        lines.append(
            f"| `{group['group']}` | `{group['decision']}` | {group['direct_hosted_oauth_paths']} | "
            f"{group['local_bridge_paths']} | "
            f"{group['blocked_or_unproven_paths']} | {group['total_paths']} | {action} |"
        )

    lines.extend(["", "## Boundary Examples", ""])
    for group in payload["groups"]:
        blocked = group.get("blocked_examples") or []
        if not blocked:
            continue
        lines.append(f"### {group['group']}")
        for row in blocked[:8]:
            meta = CATEGORY_ACTIONS.get(str(row.get("category")), CATEGORY_ACTIONS["not_probed_directly"])
            evidence = str(row.get("evidence") or "").replace("|", "\\|")
            lines.append(f"- `{row.get('path')}`: `{row.get('category')}`; {meta['action']} Evidence: `{evidence}`")
        lines.append("")
    (REPORTS / "coverage_map_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any], *, group_filter: str | None, limit: int) -> None:
    print("OpenAI OAuth bridge coverage map:", "complete" if payload["goal_complete"] else "not complete")
    print(payload["bottom_line"])
    print()
    groups = payload["groups"]
    if group_filter:
        groups = [group for group in groups if group["group"] == group_filter]
    for group in groups[:limit]:
        print(
            f"- {group['group']}: {group['decision']} "
            f"(direct_oauth={group['direct_hosted_oauth_paths']}, "
            f"local_bridge={group['local_bridge_paths']}, "
            f"blocked_or_unproven={group['blocked_or_unproven_paths']}, total={group['total_paths']})"
        )
        print(f"  {group['action']}")
        blocked = group.get("blocked_examples") or []
        for row in blocked[:3]:
            print(f"  - {row.get('path')}: {row.get('category')}")
    remaining = len(groups) - min(limit, len(groups))
    if remaining > 0:
        print(f"... {remaining} more groups in reports/coverage_map_latest.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate product-group coverage for the OAuth bridge.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--group", help="Print only one product group, such as realtime or organization/admin.")
    parser.add_argument("--limit", type=int, default=30, help="Number of groups to print.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/coverage_map_latest.*.")
    args = parser.parse_args()

    payload = build_report()
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload, group_filter=args.group, limit=max(args.limit, 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
