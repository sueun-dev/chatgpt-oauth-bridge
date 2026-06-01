from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict


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


def all_pass(report: Dict[str, Any]) -> bool:
    results = report.get("results")
    return isinstance(results, list) and bool(results) and all(
        isinstance(row, dict) and row.get("status") == "pass"
        for row in results
    )


def result_count(report: Dict[str, Any]) -> int:
    results = report.get("results")
    return len(results) if isinstance(results, list) else 0


def build_report() -> Dict[str, Any]:
    surface = load_json("openai_surface_audit_latest.json")
    proxy = load_json("proxy_smoke_latest.json")
    sdk = load_json("openai_sdk_proxy_smoke_latest.json")
    offline = load_json("router_offline_smoke_latest.json")
    environment = load_json("environment_latest.json")
    matrix = load_json("latest.json")

    counts = surface.get("category_counts") if isinstance(surface.get("category_counts"), dict) else {}
    api_key_required = int(counts.get("api_key_or_admin_key_required", 0) or 0)
    direct_oauth = int(counts.get("direct_official_oauth_verified", 0) or 0)
    local_bridge = int(counts.get("local_compat_or_chatgpt_backend_bridge", 0) or 0)
    official_paths = int(surface.get("official_paths_count", 0) or 0)
    incomplete_or_resource_bound = (
        int(counts.get("resource_bound_not_fully_verified", 0) or 0)
        + int(counts.get("official_route_auth_reached_but_not_complete", 0) or 0)
        + int(counts.get("not_available_current_deployment", 0) or 0)
    )

    requirements = [
        {
            "requirement": "Documented OpenAI API surface has direct OAuth proof or explicit local/ChatGPT compatibility coverage",
            "status": "not_met" if api_key_required or incomplete_or_resource_bound else "met",
            "evidence": (
                f"official_paths={official_paths}; direct_oauth={direct_oauth}; "
                f"local_bridge={local_bridge}; api_key_or_admin_key_required={api_key_required}; "
                f"incomplete_or_resource_bound={incomplete_or_resource_bound}"
            ),
        },
        {
            "requirement": "Legal local/ChatGPT-backend compatibility routes exist for common app workflows",
            "status": "met" if local_bridge > 0 else "not_met",
            "evidence": f"local_compat_or_chatgpt_backend_bridge={local_bridge}",
        },
        {
            "requirement": "Local router compatibility logic passes without network or localhost sockets",
            "status": "met" if all_pass(offline) else "not_met",
            "evidence": f"offline_results={result_count(offline)}; report=reports/router_offline_smoke_latest.json",
        },
        {
            "requirement": "Current environment can reach Codex model discovery",
            "status": "met" if (environment.get("codex_model_discovery") or {}).get("ok") is True else "not_met",
            "evidence": (
                f"ok={(environment.get('codex_model_discovery') or {}).get('ok')}; "
                f"http_status={(environment.get('codex_model_discovery') or {}).get('http_status')}; "
                f"model_count={(environment.get('codex_model_discovery') or {}).get('model_count')}; "
                f"error={(environment.get('codex_model_discovery') or {}).get('error')}"
            ),
        },
        {
            "requirement": "Current environment can bind localhost for HTTP/SDK smoke",
            "status": "met" if (environment.get("localhost_bind") or {}).get("ok") is True else "not_met",
            "evidence": (
                f"ok={(environment.get('localhost_bind') or {}).get('ok')}; "
                f"host={(environment.get('localhost_bind') or {}).get('host')}; "
                f"port={(environment.get('localhost_bind') or {}).get('port')}; "
                f"error={(environment.get('localhost_bind') or {}).get('error')}"
            ),
        },
        {
            "requirement": "HTTP proxy smoke has a passing latest report",
            "status": "met" if all_pass(proxy) else "not_met",
            "evidence": f"proxy_results={result_count(proxy)}; finished_at={proxy.get('finished_at')}",
        },
        {
            "requirement": "Official OpenAI Python SDK smoke has a passing latest report",
            "status": "met" if all_pass(sdk) else "not_met",
            "evidence": f"sdk_results={result_count(sdk)}; finished_at={sdk.get('finished_at')}",
        },
        {
            "requirement": "OAuth matrix has a current evidence report",
            "status": "met" if result_count(matrix) > 0 else "not_met",
            "evidence": f"matrix_results={result_count(matrix)}; finished_at={matrix.get('finished_at')}",
        },
    ]

    blockers = []
    if api_key_required:
        blockers.append(
            f"{api_key_required} documented OpenAI API paths remain API-key/Admin-key boundaries."
        )
    if incomplete_or_resource_bound:
        blockers.append(
            f"{incomplete_or_resource_bound} documented paths are resource-bound, incomplete, or unavailable in the current deployment."
        )
    if not all_pass(proxy):
        blockers.append("Latest HTTP proxy smoke report is missing or not fully passing.")
    if not all_pass(sdk):
        blockers.append("Latest OpenAI Python SDK proxy smoke report is missing or not fully passing.")
    env_model = environment.get("codex_model_discovery") or {}
    env_bind = environment.get("localhost_bind") or {}
    env_diagnostics = environment.get("diagnostics") if isinstance(environment.get("diagnostics"), dict) else {}
    if env_model.get("ok") is not True:
        blockers.append("Current environment cannot reach Codex model discovery.")
    if env_bind.get("ok") is not True:
        blockers.append("Current environment cannot bind localhost for HTTP/SDK smoke.")
    environment_warnings = []
    if env_model.get("ok") is not True:
        environment_warnings.append("Current environment cannot reach Codex model discovery.")
    if env_bind.get("ok") is not True:
        environment_warnings.append("Current environment cannot bind localhost for HTTP/SDK smoke.")
    surface_blocked = bool(api_key_required or incomplete_or_resource_bound)

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "goal_complete": False if blockers else True,
        "hosted_oauth_complete": direct_oauth == official_paths,
        "local_bridge_surface_complete": not bool(api_key_required or incomplete_or_resource_bound),
        "bottom_line": (
            "Not complete: the bridge is useful and locally verified, but current evidence does not show "
            "that every documented OpenAI API path is covered by direct OAuth or explicit local compatibility."
            if surface_blocked
            else (
                "Not complete: every documented path is mapped to direct OAuth or explicit local compatibility, "
                f"but only {direct_oauth} paths are direct hosted OAuth and this environment cannot prove live "
                "Codex network access and localhost SDK smoke."
            )
            if blockers
            else "Complete under the current evidence set."
        ),
        "surface_audit": {
            "generated_at": surface.get("generated_at"),
            "openapi_source": surface.get("openapi_source"),
            "official_paths_count": official_paths,
            "category_counts": counts,
        },
        "reports": {
            "oauth_matrix": {"results": result_count(matrix), "finished_at": matrix.get("finished_at")},
            "proxy_smoke": {"results": result_count(proxy), "finished_at": proxy.get("finished_at"), "all_pass": all_pass(proxy)},
            "sdk_smoke": {"results": result_count(sdk), "finished_at": sdk.get("finished_at"), "all_pass": all_pass(sdk)},
            "offline_smoke": {"results": result_count(offline), "finished_at": offline.get("finished_at"), "all_pass": all_pass(offline)},
            "environment": {
                "finished_at": environment.get("generated_at"),
                "codex_model_discovery_ok": env_model.get("ok"),
                "codex_model_discovery_error_type": env_model.get("error_type"),
                "localhost_bind_ok": env_bind.get("ok"),
                "localhost_bind_error_type": env_bind.get("error_type"),
                "dns_or_network_blocked": env_diagnostics.get("dns_or_network_blocked"),
                "localhost_socket_denied": env_diagnostics.get("localhost_socket_denied"),
            },
        },
        "requirements": requirements,
        "blockers": blockers,
        "environment_warnings": environment_warnings,
    }
    return payload


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "readiness_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    lines = [
        "# OAuth Bridge Readiness",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Goal complete: `{payload['goal_complete']}`",
        f"- Hosted OpenAI OAuth complete: `{payload['hosted_oauth_complete']}`",
        f"- Local bridge surface complete: `{payload['local_bridge_surface_complete']}`",
        f"- Bottom line: {payload['bottom_line']}",
        "",
        "## Surface Audit",
        "",
        f"- OpenAPI source: `{payload['surface_audit'].get('openapi_source')}`",
        f"- Official paths: `{payload['surface_audit'].get('official_paths_count')}`",
        "",
        "| Category | Count |",
        "|---|---:|",
    ]
    counts = payload["surface_audit"].get("category_counts") or {}
    for key, value in sorted(counts.items()):
        lines.append(f"| `{key}` | {value} |")
    lines.extend([
        "",
        "## Requirements",
        "",
        "| Status | Requirement | Evidence |",
        "|---|---|---|",
    ])
    for item in payload["requirements"]:
        evidence = str(item["evidence"]).replace("|", "\\|")
        lines.append(f"| `{item['status']}` | {item['requirement']} | `{evidence}` |")
    if payload["blockers"]:
        lines.extend(["", "## Blockers", ""])
        for blocker in payload["blockers"]:
            lines.append(f"- {blocker}")
    if payload.get("environment_warnings"):
        lines.extend(["", "## Current Environment Warnings", ""])
        for warning in payload["environment_warnings"]:
            lines.append(f"- {warning}")
    lines.append("")
    (REPORTS / "readiness_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any]) -> None:
    print("OAuth bridge readiness:", "complete" if payload["goal_complete"] else "not complete")
    print(payload["bottom_line"])
    print()
    for item in payload["requirements"]:
        print(f"- {item['status']}: {item['requirement']}")
        print(f"  {item['evidence']}")
    if payload["blockers"]:
        print()
        print("Blockers:")
        for blocker in payload["blockers"]:
            print(f"- {blocker}")
    if payload.get("environment_warnings"):
        print()
        print("Current environment warnings:")
        for warning in payload["environment_warnings"]:
            print(f"- {warning}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize current OAuth bridge readiness against the full goal.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/readiness_latest.*.")
    args = parser.parse_args()

    payload = build_report()
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
