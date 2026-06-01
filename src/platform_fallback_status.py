from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from platform_fallback import (
    ACCESS_TOKEN_ENV,
    ADMIN_KEY_ENV,
    API_KEY_ENV,
    BASE_URL_ENV,
    ENABLE_ENV,
    MODE_ENV,
    global_fallback_state,
    path_fallback_state,
)
from classify_openai_path import classify


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DEFAULT_PATHS = [
    "/v1/videos/edits",
    "/v1/fine_tuning/jobs/ftjob_123/cancel",
    "/v1/organization/projects",
]


def path_state(path: str) -> Dict[str, Any]:
    payload = classify(path)
    match = payload.get("match") if isinstance(payload.get("match"), dict) else {}
    category = str(match.get("category") or "not_in_surface_audit")
    state = path_fallback_state(path, category=category)
    return {
        "path": path,
        "ok": payload.get("ok"),
        "normalized_path": payload.get("normalized_path"),
        "matched_path": payload.get("matched_path"),
        "match_type": payload.get("match_type"),
        "category": category,
        "support": match.get("support"),
        "evidence": match.get("evidence"),
        "fallback": state,
    }


def build_report(paths: List[str]) -> Dict[str, Any]:
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "object": "oauth_compat.platform_fallback_status",
        "global": global_fallback_state(),
        "paths": [path_state(path) for path in paths],
        "setup": {
            "enable": f"export {ENABLE_ENV}=1",
            "prefer_mode": f"export {MODE_ENV}=prefer",
            "boundary_mode": f"export {MODE_ENV}=boundary",
            "api_key": f"export {API_KEY_ENV}=sk-...",
            "admin_key": f"export {ADMIN_KEY_ENV}=sk-admin-or-ek-...",
            "platform_bearer": f"export {ACCESS_TOKEN_ENV}=official-workload-identity-bearer",
            "base_url": f"export {BASE_URL_ENV}=https://api.openai.com/v1",
        },
        "warnings": [
            "This is not ChatGPT/Codex OAuth. It is an explicit Platform/Admin credential fallback.",
            "OPENAI_ACCESS_TOKEN is for official OpenAI workload identity federation style bearer tokens, not a ChatGPT/Codex OAuth session token.",
            "The local SDK placeholder value oauth-local-proxy is ignored as a Platform credential.",
            "The local proxy never prints or stores the key value in reports.",
            "Keep Admin credentials separate; organization and project administration paths require the admin-key environment.",
        ],
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "platform_fallback_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    lines = [
        "# Platform Fallback Status",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Enabled: `{payload['global']['enabled']}`",
        f"- Mode: `{payload['global']['mode']}`",
        f"- Base URL: `{payload['global']['base_url']}`",
        f"- API key present: `{payload['global']['api_key_present']}`",
        f"- Access token present: `{payload['global']['access_token_present']}`",
        f"- Admin key present: `{payload['global']['admin_key_present']}`",
        "",
        "## Setup",
        "",
        "```bash",
        payload["setup"]["enable"],
        payload["setup"]["boundary_mode"],
        "# or, for exact hosted API behavior before local compatibility:",
        payload["setup"]["prefer_mode"],
        payload["setup"]["api_key"],
        payload["setup"]["platform_bearer"],
        payload["setup"]["admin_key"],
        payload["setup"]["base_url"],
        "```",
        "",
        "## Path Checks",
        "",
        "| Path | Matched Path | Category | Mode | Credential Env | Accepted Envs | Present | Can Forward |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in payload["paths"]:
        fallback = row["fallback"]
        accepted_envs = ", ".join(fallback.get("credential_envs") or [fallback.get("credential_env")])
        lines.append(
            f"| `{row.get('path')}` | `{row.get('matched_path')}` | `{row.get('category')}` | "
            f"`{fallback.get('mode')}` | "
            f"`{fallback.get('credential_env')}` | `{accepted_envs}` | `{fallback.get('credential_present')}` | `{fallback.get('can_forward')}` |"
        )
    lines.extend(["", "## Warnings", ""])
    for warning in payload["warnings"]:
        lines.append(f"- {warning}")
    lines.append("")
    (REPORTS / "platform_fallback_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any]) -> None:
    state = payload["global"]
    print("Platform fallback:", "enabled" if state["enabled"] else "disabled")
    print(
        f"mode={state['mode']} base_url={state['base_url']} api_key_present={state['api_key_present']} "
        f"access_token_present={state['access_token_present']} admin_key_present={state['admin_key_present']}"
    )
    print()
    for row in payload["paths"]:
        fallback = row["fallback"]
        print(
            f"- {row['path']}: {row['category']} "
            f"credential={fallback['credential_env']} accepted={','.join(fallback.get('credential_envs') or [])} "
            f"present={fallback['credential_present']} "
            f"can_forward={fallback['can_forward']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Show explicit Platform/Admin credential fallback state.")
    parser.add_argument("paths", nargs="*", default=DEFAULT_PATHS, help="OpenAI paths to check.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/platform_fallback_latest.*.")
    args = parser.parse_args()

    payload = build_report([str(path) for path in args.paths])
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
