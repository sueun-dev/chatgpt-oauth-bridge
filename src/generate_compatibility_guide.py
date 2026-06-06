from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from surface_audit import load_surface_payload


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

CATEGORY_ACTIONS = {
    "direct_official_oauth_verified": {
        "label": "Official OAuth verified",
        "action": "Can call the official OpenAI path with the tested Codex/ChatGPT OAuth token evidence. Re-run the matrix before relying on it for a different account or date.",
    },
    "local_compat_or_chatgpt_backend_bridge": {
        "label": "Use local bridge",
        "action": "Use the local OpenAI-shaped proxy at http://127.0.0.1:8787/v1 or the Python wrapper. This is compatibility, not hosted OpenAI Platform OAuth support.",
    },
    "api_key_or_admin_key_required": {
        "label": "Needs Platform credential",
        "action": "Do not route this through ChatGPT/Codex OAuth. Use a Platform API key, Admin API key, or official workload identity federation access token where applicable, or keep this feature disabled.",
    },
    "resource_bound_not_fully_verified": {
        "label": "Needs live resource proof",
        "action": "Do not claim complete support yet. A real resource id or lifecycle mutation is needed before this can be marked usable.",
    },
    "official_route_auth_reached_but_not_complete": {
        "label": "Auth reached, incomplete",
        "action": "OAuth reached route validation, but the workflow is not proven complete. Treat it as unavailable until a full create/use/delete flow passes.",
    },
    "not_available_current_deployment": {
        "label": "Not routed here",
        "action": "The documented route was not available in the tested deployment. Keep a fallback or skip the feature.",
    },
    "not_probed_directly": {
        "label": "Not probed",
        "action": "No direct evidence exists. Add a probe before exposing this path to users.",
    },
}

CATEGORY_ORDER = [
    "direct_official_oauth_verified",
    "local_compat_or_chatgpt_backend_bridge",
    "official_route_auth_reached_but_not_complete",
    "resource_bound_not_fully_verified",
    "not_available_current_deployment",
    "not_probed_directly",
    "api_key_or_admin_key_required",
]


def load_surface() -> Dict[str, Any]:
    return load_surface_payload()


def build_report() -> Dict[str, Any]:
    surface = load_surface()
    rows = [row for row in surface.get("rows", []) if isinstance(row, dict)]
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        category = str(row.get("category") or "not_probed_directly")
        grouped[category].append(row)

    categories = {}
    ordered_categories = [
        category for category in CATEGORY_ORDER if category in grouped
    ] + sorted(category for category in grouped if category not in CATEGORY_ORDER)
    for category in ordered_categories:
        category_rows = grouped[category]
        meta = CATEGORY_ACTIONS.get(category, CATEGORY_ACTIONS["not_probed_directly"])
        categories[category] = {
            "label": meta["label"],
            "action": meta["action"],
            "count": len(category_rows),
            "paths": sorted(category_rows, key=lambda row: str(row.get("path") or "")),
        }

    api_key_required = len(grouped.get("api_key_or_admin_key_required", []))
    unfinished = (
        len(grouped.get("resource_bound_not_fully_verified", []))
        + len(grouped.get("official_route_auth_reached_but_not_complete", []))
        + len(grouped.get("not_available_current_deployment", []))
        + len(grouped.get("not_probed_directly", []))
    )
    goal_complete = api_key_required == 0 and unfinished == 0
    direct = len(grouped.get("direct_official_oauth_verified", []))
    local = len(grouped.get("local_compat_or_chatgpt_backend_bridge", []))
    official_paths = int(surface.get("official_paths_count", 0) or 0)
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "goal_complete": goal_complete,
        "compatibility_map_complete": goal_complete,
        "hosted_oauth_complete": direct == official_paths,
        "bottom_line": (
            (
                "Complete as a compatibility map: every documented path has either direct OAuth evidence or a named local bridge path. "
                f"Only {direct} paths are direct hosted OAuth; {local} paths are local or ChatGPT-backend compatibility."
            )
            if goal_complete
            else "Not complete: keep direct OAuth, local compatibility, and API-key/Admin-key paths separate."
        ),
        "source": {
            "openapi_source": surface.get("openapi_source"),
            "source_warning": surface.get("source_warning"),
            "surface_generated_at": surface.get("generated_at"),
            "official_paths_count": surface.get("official_paths_count"),
            "matrix_started_at": surface.get("matrix_started_at"),
            "matrix_finished_at": surface.get("matrix_finished_at"),
        },
        "category_counts": {
            category: data["count"]
            for category, data in sorted(categories.items())
        },
        "categories": categories,
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "compatibility_guide_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))

    lines = [
        "# OAuth Compatibility Quick Guide",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Compatibility map complete: `{payload['compatibility_map_complete']}`",
        f"- Hosted OpenAI OAuth complete: `{payload['hosted_oauth_complete']}`",
        f"- Bottom line: {payload['bottom_line']}",
        f"- OpenAPI source: `{payload['source'].get('openapi_source')}`",
        f"- Official paths: `{payload['source'].get('official_paths_count')}`",
    ]
    if payload["source"].get("source_warning"):
        lines.append(f"- Source warning: {payload['source']['source_warning']}")
    lines.extend([
        "",
        "## What To Do",
        "",
        "| Category | Paths | User decision |",
        "|---|---:|---|",
    ])
    for category, data in payload["categories"].items():
        lines.append(f"| `{category}` | {data['count']} | {data['action']} |")

    lines.extend([
        "",
        "## Full Path Guide",
        "",
        "| Path | Category | Decision | Evidence |",
        "|---|---|---|---|",
    ])
    for category, data in payload["categories"].items():
        for row in data["paths"]:
            evidence = str(row.get("evidence") or "").replace("|", "\\|")
            lines.append(
                f"| `{row.get('path')}` | `{category}` | {data['label']} | `{evidence}` |"
            )
    lines.append("")
    (REPORTS / "compatibility_guide_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any], *, category: str | None, limit: int) -> None:
    print("OAuth compatibility guide:", "complete" if payload["compatibility_map_complete"] else "not complete")
    print(payload["bottom_line"])
    print()
    categories = payload["categories"]
    selected = {category: categories[category]} if category else categories
    for name, data in selected.items():
        print(f"- {name}: {data['count']}")
        print(f"  {data['action']}")
        for row in data["paths"][:limit]:
            print(f"  - {row.get('path')}: {row.get('evidence')}")
        remaining = data["count"] - min(limit, data["count"])
        if remaining > 0:
            print(f"  ... {remaining} more")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a user-facing OAuth compatibility guide from the latest surface audit.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--category", choices=sorted(CATEGORY_ACTIONS), help="Print only one category.")
    parser.add_argument("--limit", type=int, default=8, help="Number of paths to print per category in human output.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/compatibility_guide_latest.*.")
    args = parser.parse_args()

    payload = build_report()
    if args.category and args.category not in payload["categories"]:
        payload["categories"][args.category] = {
            "label": CATEGORY_ACTIONS[args.category]["label"],
            "action": CATEGORY_ACTIONS[args.category]["action"],
            "count": 0,
            "paths": [],
        }
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload, category=args.category, limit=max(args.limit, 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
