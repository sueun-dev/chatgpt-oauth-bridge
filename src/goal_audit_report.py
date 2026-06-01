from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from generate_coverage_map import build_report as build_coverage_map_report
from generate_client_config import build_report as build_client_config_report
from publish_check import build_report as build_publish_check_report
from readiness_report import build_report as build_readiness_report


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def load_json(name: str) -> Dict[str, Any]:
    path = REPORTS / name
    if not path.exists():
        return {"_missing": True, "_path": str(path)}
    try:
        payload = json.loads(path.read_text())
    except Exception as exc:
        return {"_missing": False, "_path": str(path), "_error": f"{type(exc).__name__}: {exc}"}
    return payload if isinstance(payload, dict) else {"_path": str(path), "_error": "report is not a JSON object"}


def report_all_pass(report: Dict[str, Any]) -> bool:
    results = report.get("results")
    return isinstance(results, list) and bool(results) and all(
        isinstance(row, dict) and row.get("status") == "pass"
        for row in results
    )


def report_count(report: Dict[str, Any]) -> int:
    results = report.get("results")
    return len(results) if isinstance(results, list) else 0


def coverage_groups_by_decision(coverage: Dict[str, Any], decisions: List[str]) -> List[Dict[str, Any]]:
    groups = coverage.get("groups")
    if not isinstance(groups, list):
        return []
    wanted = set(decisions)
    return [
        group
        for group in groups
        if isinstance(group, dict) and group.get("decision") in wanted
    ]


def build_requirement(
    *,
    name: str,
    status: str,
    evidence: str,
    action: str,
) -> Dict[str, str]:
    return {
        "name": name,
        "status": status,
        "evidence": evidence,
        "action": action,
    }


def build_report() -> Dict[str, Any]:
    readiness = build_readiness_report()
    coverage = build_coverage_map_report()
    client_config = build_client_config_report()
    publish = build_publish_check_report()
    surface = load_json("openai_surface_audit_latest.json")
    offline = load_json("router_offline_smoke_latest.json")
    environment = load_json("environment_latest.json")
    proxy = load_json("proxy_smoke_latest.json")
    sdk = load_json("openai_sdk_proxy_smoke_latest.json")
    matrix = load_json("latest.json")
    boundary = load_json("boundary_playbook_latest.json")
    migration = load_json("migration_plan_latest.json")

    counts = surface.get("category_counts") if isinstance(surface.get("category_counts"), dict) else {}
    official_paths = int(surface.get("official_paths_count", 0) or 0)
    direct = int(counts.get("direct_official_oauth_verified", 0) or 0)
    local = int(counts.get("local_compat_or_chatgpt_backend_bridge", 0) or 0)
    platform_boundary = int(counts.get("api_key_or_admin_key_required", 0) or 0)
    unfinished = (
        int(counts.get("resource_bound_not_fully_verified", 0) or 0)
        + int(counts.get("official_route_auth_reached_but_not_complete", 0) or 0)
        + int(counts.get("not_available_current_deployment", 0) or 0)
        + int(counts.get("not_probed_directly", 0) or 0)
    )
    ready_paths = direct + local
    hosted_oauth_complete = direct == official_paths
    local_bridge_surface_complete = not bool(platform_boundary or unfinished)
    offline_ok = report_all_pass(offline)
    env_model_ok = (environment.get("codex_model_discovery") or {}).get("ok") is True
    env_bind_ok = (environment.get("localhost_bind") or {}).get("ok") is True

    requirements = [
        build_requirement(
            name="Judge whether every OpenAI API feature has direct OAuth proof or explicit local/ChatGPT compatibility",
            status="not_met" if platform_boundary or unfinished else "met",
            evidence=(
                f"official_paths={official_paths}; direct_oauth={direct}; local_compat={local}; "
                f"api_or_admin_key_boundary={platform_boundary}; unfinished_or_resource_bound={unfinished}"
            ),
            action="Do not claim a hosted OpenAI Platform OAuth replacement just because a path has local compatibility coverage.",
        ),
        build_requirement(
            name="Include OpenAI-provided API paths that actually accept this OAuth token",
            status="met" if direct > 0 else "not_met",
            evidence=f"direct_official_oauth_verified={direct}; matrix_results={report_count(matrix)}",
            action="Keep these paths classified separately from local compatibility and Platform fallback.",
        ),
        build_requirement(
            name="Include safe local or ChatGPT-backend workarounds where direct OAuth is unavailable",
            status="met" if local > 0 and offline_ok else "not_met",
            evidence=f"local_compat_or_chatgpt_backend_bridge={local}; offline_results={report_count(offline)}; offline_all_pass={offline_ok}",
            action="Use local compatibility only where the router smoke and docs name the boundary clearly.",
        ),
        build_requirement(
            name="Expose API/Admin-key boundaries without pretending OAuth can bypass them",
            status="met" if platform_boundary >= 0 and not boundary.get("_missing") else "not_met",
            evidence=(
                f"api_or_admin_key_boundary={platform_boundary}; "
                f"boundary_report_missing={boundary.get('_missing') is True}"
            ),
            action="Use bridge.py boundaries and optional Platform fallback for these paths.",
        ),
        build_requirement(
            name="Make the bridge easy for users to configure, check, and migrate",
            status="met" if client_config.get("base_url") and not migration.get("_missing") else "not_met",
            evidence=(
                f"base_url={client_config.get('base_url')}; "
                f"placeholder_api_key={client_config.get('placeholder_api_key')}; "
                f"migration_report_missing={migration.get('_missing') is True}"
            ),
            action="Use bridge.py quickstart, config, check, migrate, status, coverage, publish-check, and verdict as the user-facing entrypoints.",
        ),
        build_requirement(
            name="Make GitHub and clone-user publish state explicit before public use",
            status="met" if publish.get("publish_ready") is True else "not_met",
            evidence=(
                f"publish_ready={publish.get('publish_ready')}; "
                f"local_tree_ready={publish.get('local_tree_ready')}; "
                f"changed_total={(publish.get('counts') or {}).get('changed_total')}; "
                f"untracked_source={(publish.get('counts') or {}).get('untracked_source')}; "
                f"head_matches_upstream={(publish.get('branch') or {}).get('head_matches_upstream')}"
            ),
            action="Run python bridge.py publish-check --strict, then commit and push before claiming GitHub or clone users have the latest bridge.",
        ),
        build_requirement(
            name="Verify live HTTP/SDK behavior in the current environment",
            status="met" if env_model_ok and env_bind_ok and report_all_pass(proxy) and report_all_pass(sdk) else "not_met",
            evidence=(
                f"codex_model_discovery_ok={env_model_ok}; localhost_bind_ok={env_bind_ok}; "
                f"proxy_results={report_count(proxy)}; sdk_results={report_count(sdk)}"
            ),
            action="Run python bridge.py live-check from a shell with network access and localhost bind permission before launch claims.",
        ),
    ]

    ready_groups = coverage_groups_by_decision(coverage, ["usable_without_platform_key"])
    mixed_groups = coverage_groups_by_decision(coverage, ["mixed"])
    platform_groups = coverage_groups_by_decision(coverage, ["platform_credentials_required", "blocked_or_unproven"])
    unmet = [row for row in requirements if row["status"] != "met"]
    surface_has_gap = bool(platform_boundary or unfinished)

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": "complete" if not unmet else "not_complete",
        "goal_complete": False if unmet else readiness.get("goal_complete") is True,
        "hosted_oauth_complete": hosted_oauth_complete,
        "local_bridge_surface_complete": local_bridge_surface_complete,
        "bottom_line": (
            "Not complete: the bridge is user-usable for supported paths, but it is not a full OpenAI Platform API OAuth replacement."
            if unmet and surface_has_gap
            else (
                "Not complete: the documented path surface is covered by direct OAuth or explicit local compatibility, "
                f"but only {direct} paths are direct hosted OAuth and this environment cannot prove live HTTP/SDK behavior."
            )
            if unmet
            else "Complete under the current evidence set."
        ),
        "counts": {
            "official_paths": official_paths,
            "direct_official_oauth_verified": direct,
            "local_compat_or_chatgpt_backend_bridge": local,
            "usable_without_platform_key": ready_paths,
            "hosted_oauth_complete": hosted_oauth_complete,
            "local_bridge_surface_complete": local_bridge_surface_complete,
            "api_key_or_admin_key_required": platform_boundary,
            "unfinished_or_resource_bound": unfinished,
        },
        "requirements": requirements,
        "ready_groups": [
            {
                "group": group.get("group"),
                "ready_paths": group.get("ready_paths"),
                "total_paths": group.get("total_paths"),
            }
            for group in ready_groups
        ],
        "mixed_or_boundary_groups": [
            {
                "group": group.get("group"),
                "decision": group.get("decision"),
                "ready_paths": group.get("ready_paths"),
                "blocked_or_unproven_paths": group.get("blocked_or_unproven_paths"),
                "total_paths": group.get("total_paths"),
            }
            for group in [*mixed_groups, *platform_groups]
        ],
        "user_entrypoints": {
            "start_proxy": (client_config.get("commands") or {}).get("start_proxy"),
            "quickstart": "python bridge.py quickstart",
            "status": "python bridge.py status",
            "verdict": "python bridge.py verdict",
            "doctor": "python bridge.py doctor",
            "live_check": "python bridge.py live-check",
            "publish_check": "python bridge.py publish-check",
            "check_app": "python bridge.py check path/to/your/app --fail-on-boundary",
            "migration_plan": "python bridge.py migrate path/to/your/app --fail-on-boundary",
            "coverage": "python bridge.py coverage",
            "boundaries": "python bridge.py boundaries",
            "config": "python bridge.py config",
        },
        "do_not_claim": [
            "Do not claim ChatGPT/Codex OAuth is a general OpenAI Platform credential.",
            "Do not claim hosted Platform behavior is handled without official Platform/Admin credentials when the bridge uses a local substitute.",
            "Do not call local compatibility aliases direct hosted OpenAI OAuth proof.",
            "Do not call live HTTP/SDK behavior current in this environment while network and localhost bind probes fail.",
        ],
        "next_actions": [row["action"] for row in unmet],
        "source": {
            "readiness_goal_complete": readiness.get("goal_complete"),
            "coverage_goal_complete": coverage.get("goal_complete"),
            "surface_openapi_source": surface.get("openapi_source"),
            "surface_source_warning": surface.get("source_warning"),
        },
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "goal_audit_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))

    lines = [
        "# OAuth Bridge Goal Audit",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Verdict: `{payload['verdict']}`",
        f"- Goal complete: `{payload['goal_complete']}`",
        f"- Hosted OpenAI OAuth complete: `{payload['hosted_oauth_complete']}`",
        f"- Local bridge surface complete: `{payload['local_bridge_surface_complete']}`",
        f"- Bottom line: {payload['bottom_line']}",
        "",
        "## Counts",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ]
    for key, value in payload["counts"].items():
        lines.append(f"| `{key}` | {value} |")

    lines.extend([
        "",
        "## Requirement Audit",
        "",
        "| Status | Requirement | Evidence | Action |",
        "|---|---|---|---|",
    ])
    for row in payload["requirements"]:
        lines.append(
            f"| `{row['status']}` | {row['name']} | `{row['evidence']}` | {row['action']} |"
        )

    lines.extend([
        "",
        "## Ready Product Groups",
        "",
        "| Group | Ready Paths | Total Paths |",
        "|---|---:|---:|",
    ])
    for group in payload["ready_groups"]:
        lines.append(f"| `{group.get('group')}` | {group.get('ready_paths')} | {group.get('total_paths')} |")

    lines.extend([
        "",
        "## Mixed Or Boundary Groups",
        "",
        "| Group | Decision | Ready | Blocked Or Unproven | Total |",
        "|---|---|---:|---:|---:|",
    ])
    for group in payload["mixed_or_boundary_groups"]:
        lines.append(
            f"| `{group.get('group')}` | `{group.get('decision')}` | "
            f"{group.get('ready_paths')} | {group.get('blocked_or_unproven_paths')} | {group.get('total_paths')} |"
        )

    lines.extend([
        "",
        "## User Entrypoints",
        "",
    ])
    for name, command in payload["user_entrypoints"].items():
        lines.append(f"- `{name}`: `{command}`")

    lines.extend([
        "",
        "## Do Not Claim",
        "",
    ])
    for item in payload["do_not_claim"]:
        lines.append(f"- {item}")

    lines.extend([
        "",
        "## Next Actions",
        "",
    ])
    for action in payload["next_actions"]:
        lines.append(f"- {action}")
    lines.append("")
    (REPORTS / "goal_audit_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any]) -> None:
    print("OAuth bridge verdict:", payload["verdict"])
    print(payload["bottom_line"])
    print()
    counts = payload["counts"]
    print(
        "coverage="
        f"official_paths={counts['official_paths']}; "
        f"direct_oauth={counts['direct_official_oauth_verified']}; "
        f"local_bridge={counts['local_compat_or_chatgpt_backend_bridge']}; "
        f"api_or_admin_key_required={counts['api_key_or_admin_key_required']}; "
        f"unfinished_or_resource_bound={counts['unfinished_or_resource_bound']}"
    )
    print()
    print("Requirement audit:")
    for row in payload["requirements"]:
        print(f"- {row['status']}: {row['name']}")
        print(f"  {row['evidence']}")
    print()
    print("User entrypoints:")
    for name, command in payload["user_entrypoints"].items():
        print(f"- {name}: {command}")
    print()
    print("Do not claim:")
    for item in payload["do_not_claim"]:
        print(f"- {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the OAuth bridge against the user's full-goal objective.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/goal_audit_latest.*.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero unless the full-goal verdict is complete.",
    )
    args = parser.parse_args()

    payload = build_report()
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload)
    return 0 if not args.strict or payload.get("goal_complete") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
