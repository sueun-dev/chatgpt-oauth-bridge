from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from platform_fallback import (
    ACCESS_TOKEN_ENV,
    ADMIN_KEY_ENV,
    API_KEY_ENV,
    ENABLE_ENV,
    MODE_ENV,
    credential_envs_for_path,
)
from surface_audit import load_surface_payload


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def load_surface() -> Dict[str, Any]:
    return load_surface_payload()


def local_path(path: str) -> str:
    return path if path.startswith("/v1/") else f"/v1{path}"


def policy_for_category(category: str, path: str) -> Dict[str, Any]:
    if category == "direct_official_oauth_verified":
        return {
            "route_policy": "allow",
            "mode": "direct_official_oauth_or_local_proxy",
            "local_proxy_allowed": True,
            "local_bridge_allowed": True,
            "oauth_only_allowed": True,
            "hosted_oauth_verified": True,
            "local_substitute": False,
            "platform_fallback_allowed": False,
            "credential_envs": [],
            "user_action": "Use the local proxy or the tested direct official OAuth path. Re-run the OAuth matrix for a different account or date.",
        }
    if category == "local_compat_or_chatgpt_backend_bridge":
        return {
            "route_policy": "allow",
            "mode": "local_proxy_compatibility",
            "local_proxy_allowed": True,
            "local_bridge_allowed": True,
            "oauth_only_allowed": False,
            "hosted_oauth_verified": False,
            "local_substitute": True,
            "platform_fallback_allowed": False,
            "credential_envs": [],
            "user_action": "Use the local proxy. This is compatibility, not proof that the hosted OpenAI Platform route accepts ChatGPT/Codex OAuth.",
        }
    if category == "api_key_or_admin_key_required":
        return {
            "route_policy": "deny_in_oauth_only",
            "mode": "platform_fallback_or_disabled",
            "local_proxy_allowed": False,
            "local_bridge_allowed": False,
            "oauth_only_allowed": False,
            "hosted_oauth_verified": False,
            "local_substitute": False,
            "platform_fallback_allowed": True,
            "credential_envs": credential_envs_for_path(path),
            "user_action": "Disable this feature for OAuth-only deployments or enable explicit Platform/Admin fallback with the listed credential env.",
        }
    if category == "resource_bound_not_fully_verified":
        return {
            "route_policy": "needs_live_resource_proof",
            "mode": "resource_bound",
            "local_proxy_allowed": False,
            "local_bridge_allowed": False,
            "oauth_only_allowed": False,
            "hosted_oauth_verified": False,
            "local_substitute": False,
            "platform_fallback_allowed": True,
            "credential_envs": credential_envs_for_path(path),
            "user_action": "Do not mark this complete until a real resource ID is available and the mutation is safely verified.",
        }
    if category == "official_route_auth_reached_but_not_complete":
        return {
            "route_policy": "needs_more_proof",
            "mode": "auth_reached_but_incomplete",
            "local_proxy_allowed": False,
            "local_bridge_allowed": False,
            "oauth_only_allowed": False,
            "hosted_oauth_verified": False,
            "local_substitute": False,
            "platform_fallback_allowed": True,
            "credential_envs": credential_envs_for_path(path),
            "user_action": "Keep disabled or on Platform fallback until live proof covers the full workflow.",
        }
    if category == "not_available_current_deployment":
        return {
            "route_policy": "deny_in_oauth_only",
            "mode": "not_available_current_deployment",
            "local_proxy_allowed": False,
            "local_bridge_allowed": False,
            "oauth_only_allowed": False,
            "hosted_oauth_verified": False,
            "local_substitute": False,
            "platform_fallback_allowed": True,
            "credential_envs": credential_envs_for_path(path),
            "user_action": "Keep disabled or use official Platform credentials if the hosted deployment supports it.",
        }
    return {
        "route_policy": "review_required",
        "mode": "not_probed_or_unknown",
        "local_proxy_allowed": False,
        "local_bridge_allowed": False,
        "oauth_only_allowed": False,
        "hosted_oauth_verified": False,
        "local_substitute": False,
        "platform_fallback_allowed": False,
        "credential_envs": credential_envs_for_path(path),
        "user_action": "Review this path before enabling it.",
    }


def build_report() -> Dict[str, Any]:
    surface = load_surface()
    rows = [row for row in surface.get("rows", []) if isinstance(row, dict)]
    entries: List[Dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: str(item.get("path") or "")):
        path = str(row.get("path") or "")
        category = str(row.get("category") or "not_probed_directly")
        policy = policy_for_category(category, path)
        entries.append({
            "path": path,
            "local_path": local_path(path),
            "category": category,
            "support": row.get("support"),
            "evidence": row.get("evidence"),
            **policy,
        })

    local_bridge_allowlist = [entry["local_path"] for entry in entries if entry["route_policy"] == "allow"]
    local_bridge_denylist = [entry["local_path"] for entry in entries if entry["route_policy"] != "allow"]
    hosted_oauth_allowlist = [entry["local_path"] for entry in entries if entry["hosted_oauth_verified"]]
    hosted_oauth_denylist = [entry["local_path"] for entry in entries if not entry["hosted_oauth_verified"]]
    local_substitutes = [entry["local_path"] for entry in entries if entry["local_substitute"]]
    fallback = [entry["local_path"] for entry in entries if entry["platform_fallback_allowed"]]
    resource_bound = [
        entry["local_path"]
        for entry in entries
        if entry["category"] == "resource_bound_not_fully_verified"
    ]
    local_bridge_complete = not local_bridge_denylist
    hosted_oauth_complete = len(hosted_oauth_allowlist) == len(entries)
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "object": "oauth_compat.route_policy",
        "goal_complete": local_bridge_complete,
        "local_bridge_policy_complete": local_bridge_complete,
        "hosted_oauth_complete": hosted_oauth_complete,
        "bottom_line": (
            "Not complete: the local bridge route policy does not cover every documented OpenAI path."
            if local_bridge_denylist
            else (
                "Local bridge policy covers every documented path, but strict hosted OpenAI OAuth is verified only "
                f"for {len(hosted_oauth_allowlist)} paths; local compatibility is not hosted Platform OAuth."
            )
        ),
        "source": {
            "openapi_source": surface.get("openapi_source"),
            "source_warning": surface.get("source_warning"),
            "official_paths_count": surface.get("official_paths_count"),
            "surface_generated_at": surface.get("generated_at"),
        },
        "summary": {
            "total_paths": len(entries),
            "direct_hosted_oauth_verified": len(hosted_oauth_allowlist),
            "local_bridge_compatibility": len(local_substitutes),
            "allow_local_bridge": len(local_bridge_allowlist),
            "deny_local_bridge": len(local_bridge_denylist),
            "allow_oauth_only": len(hosted_oauth_allowlist),
            "deny_oauth_only": len(hosted_oauth_denylist),
            "platform_fallback_candidates": len(fallback),
            "resource_bound": len(resource_bound),
        },
        "env": {
            "enable_platform_fallback": ENABLE_ENV,
            "fallback_mode": MODE_ENV,
            "api_key": API_KEY_ENV,
            "admin_key": ADMIN_KEY_ENV,
            "official_access_token": ACCESS_TOKEN_ENV,
        },
        "allowlist_oauth_only": hosted_oauth_allowlist,
        "denylist_oauth_only": hosted_oauth_denylist,
        "allowlist_local_bridge": local_bridge_allowlist,
        "denylist_local_bridge": local_bridge_denylist,
        "local_substitute_paths": local_substitutes,
        "platform_fallback_candidates": fallback,
        "resource_bound_paths": resource_bound,
        "entries": entries,
        "consumer_guidance": [
            "Use allowlist_oauth_only only for paths with direct hosted OpenAI OAuth evidence.",
            "Use allowlist_local_bridge for local-proxy deployments; local substitutes are not hosted Platform OAuth proof.",
            "Block denylist_local_bridge unless the app explicitly enables Platform/Admin fallback or has live resource proof.",
            "Treat local_compat_or_chatgpt_backend_bridge as local compatibility, not hosted OpenAI OAuth support.",
            "Use reports/openai_bridge_ci_gate.sh path/to/app in CI to prevent accidental boundary routes.",
        ],
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "openai_bridge_route_policy.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    csv_path = REPORTS / "openai_bridge_route_policy.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            lineterminator="\n",
            fieldnames=[
                "path",
                "local_path",
                "category",
                "route_policy",
                "mode",
                "local_proxy_allowed",
                "local_bridge_allowed",
                "oauth_only_allowed",
                "hosted_oauth_verified",
                "local_substitute",
                "platform_fallback_allowed",
                "credential_envs",
                "user_action",
                "evidence",
            ],
        )
        writer.writeheader()
        for entry in payload["entries"]:
            row = {key: entry.get(key) for key in writer.fieldnames}
            row["credential_envs"] = ",".join(entry.get("credential_envs") or [])
            writer.writerow(row)

    lines = [
        "# OpenAI Bridge Route Policy",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Local bridge policy complete: `{payload['local_bridge_policy_complete']}`",
        f"- Hosted OpenAI OAuth complete: `{payload['hosted_oauth_complete']}`",
        f"- Bottom line: {payload['bottom_line']}",
        f"- Official paths: `{payload['source'].get('official_paths_count')}`",
        f"- Direct hosted OAuth verified: `{payload['summary']['direct_hosted_oauth_verified']}`",
        f"- Local bridge compatibility: `{payload['summary']['local_bridge_compatibility']}`",
        f"- Allow local bridge: `{payload['summary']['allow_local_bridge']}`",
        f"- Deny local bridge: `{payload['summary']['deny_local_bridge']}`",
        f"- Strict hosted OAuth allow: `{payload['summary']['allow_oauth_only']}`",
        f"- Strict hosted OAuth deny: `{payload['summary']['deny_oauth_only']}`",
        f"- Platform fallback candidates: `{payload['summary']['platform_fallback_candidates']}`",
        "- JSON: `reports/openai_bridge_route_policy.json`",
        "- CSV: `reports/openai_bridge_route_policy.csv`",
        "",
        "## Consumer Guidance",
        "",
    ]
    for item in payload["consumer_guidance"]:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Policy Rows",
        "",
        "| Local Path | Category | Policy | Mode | Credential Envs | Action |",
        "|---|---|---|---|---|---|",
    ])
    for entry in payload["entries"]:
        envs = ", ".join(entry.get("credential_envs") or [])
        action = str(entry.get("user_action") or "").replace("|", "\\|")
        lines.append(
            f"| `{entry['local_path']}` | `{entry['category']}` | `{entry['route_policy']}` | "
            f"`{entry['mode']}` | `{envs}` | {action} |"
        )
    lines.append("")
    (REPORTS / "openai_bridge_route_policy.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any], *, limit: int) -> None:
    print("OpenAI bridge route policy:", "complete" if payload["local_bridge_policy_complete"] else "not complete")
    print(payload["bottom_line"])
    print(
        "summary="
        f"total={payload['summary']['total_paths']}; "
        f"direct_hosted_oauth={payload['summary']['direct_hosted_oauth_verified']}; "
        f"local_bridge_compat={payload['summary']['local_bridge_compatibility']}; "
        f"allow_local_bridge={payload['summary']['allow_local_bridge']}; "
        f"deny_local_bridge={payload['summary']['deny_local_bridge']}; "
        f"platform_fallback_candidates={payload['summary']['platform_fallback_candidates']}"
    )
    denied = [entry for entry in payload["entries"] if entry["route_policy"] != "allow"]
    if denied:
        print()
        print("Local bridge denied paths:")
        for entry in denied[:limit]:
            envs = ",".join(entry.get("credential_envs") or [])
            print(f"- {entry['local_path']}: {entry['route_policy']} [{entry['category']}] envs={envs}")
        remaining = len(denied) - min(limit, len(denied))
        if remaining > 0:
            print(f"... {remaining} more in reports/openai_bridge_route_policy.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate machine-readable route policy for OpenAI OAuth bridge clients.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--limit", type=int, default=20, help="Number of denied paths to print.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/openai_bridge_route_policy.*.")
    args = parser.parse_args()

    payload = build_report()
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
