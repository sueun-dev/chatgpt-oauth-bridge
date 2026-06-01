from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DOCS = [
    ROOT / "README.md",
    ROOT / "OFFICIAL_BOUNDARY.md",
    ROOT / "RESULTS_SUMMARY.md",
]


def load_json(name: str) -> Dict[str, Any]:
    path = REPORTS / name
    if not path.exists():
        raise FileNotFoundError(f"Missing report: {path}")
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"Report is not a JSON object: {path}")
    return payload


def expected_surface_phrases(surface: Dict[str, Any]) -> List[str]:
    counts = surface.get("category_counts") if isinstance(surface.get("category_counts"), dict) else {}
    return [
        f"`{surface.get('official_paths_count')}` documented OpenAI API paths",
        f"`{counts.get('direct_official_oauth_verified', 0)}` direct official OAuth-verified paths",
        f"`{counts.get('local_compat_or_chatgpt_backend_bridge', 0)}` local/ChatGPT-backend compatibility paths",
        f"`{counts.get('api_key_or_admin_key_required', 0)}` API-key/Admin-key required",
        f"`{counts.get('not_available_current_deployment', 0)}` not available",
        f"`{counts.get('official_route_auth_reached_but_not_complete', 0)}` auth-reached-but-not-complete",
        f"`{counts.get('resource_bound_not_fully_verified', 0)}` resource-bound",
    ]


def verify_docs(surface: Dict[str, Any], offline: Dict[str, Any]) -> Dict[str, Any]:
    surface_phrases = expected_surface_phrases(surface)
    offline_results = offline.get("results") if isinstance(offline.get("results"), list) else []
    offline_passed = all(isinstance(row, dict) and row.get("status") == "pass" for row in offline_results)
    offline_phrase = f"passed `{len(offline_results)}` no-network/no-socket router checks"

    checks = []
    for path in DOCS:
        text = re.sub(r"\s+", " ", path.read_text())
        missing = [phrase for phrase in surface_phrases if phrase not in text]
        if path.name == "RESULTS_SUMMARY.md" and offline_passed and offline_phrase not in text:
            missing.append(offline_phrase)
        checks.append({
            "path": str(path.relative_to(ROOT)),
            "status": "pass" if not missing else "fail",
            "missing": missing,
        })
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "surface": {
            "generated_at": surface.get("generated_at"),
            "official_paths_count": surface.get("official_paths_count"),
            "category_counts": surface.get("category_counts"),
        },
        "offline_smoke": {
            "finished_at": offline.get("finished_at"),
            "results": len(offline_results),
            "all_pass": offline_passed,
        },
        "checks": checks,
        "ok": all(check["status"] == "pass" for check in checks),
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "summary_consistency_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    lines = [
        "# Summary Consistency",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- OK: `{payload['ok']}`",
        f"- Surface report: `{payload['surface'].get('generated_at')}`",
        f"- Official paths: `{payload['surface'].get('official_paths_count')}`",
        f"- Offline smoke results: `{payload['offline_smoke'].get('results')}`",
        "",
        "| Status | File | Missing Phrases |",
        "|---|---|---|",
    ]
    for check in payload["checks"]:
        missing = "; ".join(check.get("missing") or [])
        lines.append(f"| `{check['status']}` | `{check['path']}` | `{missing}` |")
    lines.append("")
    (REPORTS / "summary_consistency_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any]) -> None:
    print("Summary consistency:", "pass" if payload["ok"] else "fail")
    for check in payload["checks"]:
        print(f"- {check['status']}: {check['path']}")
        for phrase in check.get("missing") or []:
            print(f"  missing: {phrase}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify summary docs match the latest OAuth surface and smoke reports.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/summary_consistency_latest.*.")
    args = parser.parse_args()

    surface = load_json("openai_surface_audit_latest.json")
    offline = load_json("router_offline_smoke_latest.json")
    payload = verify_docs(surface, offline)
    if not args.no_write:
        write_reports(payload)
    print_human(payload)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
