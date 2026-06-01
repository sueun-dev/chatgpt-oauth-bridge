from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SKIP_DIRS = {".git", ".venv", ".pycache", "artifacts", "data", "__pycache__"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pcm16", ".wav", ".pyc"}
REQUIRED_REPORTS = [
    "latest.md",
    "deep_oauth_research_latest.md",
    "codex_apps_tools_latest.md",
    "openai_surface_audit_latest.md",
    "compatibility_guide_latest.md",
    "coverage_map_latest.md",
    "openai_bridge_route_policy.md",
    "openai_bridge_route_policy.csv",
    "boundary_playbook_latest.md",
    "client_config_latest.md",
    "quickstart_latest.md",
    "openai_bridge.env.example",
    "openai_bridge_ci_gate.sh",
    "openai_bridge_launch_gate.sh",
    "openai_bridge_publish_gate.sh",
    "openai_bridge_finish_gate.sh",
    "status_latest.md",
    "usage_check_latest.md",
    "migration_plan_latest.md",
    "doctor_latest.md",
    "platform_fallback_latest.md",
    "goal_audit_latest.md",
    "publish_check_latest.md",
    "summary_consistency_latest.md",
    "usage_scanner_coverage_latest.md",
    "proxy_smoke_latest.md",
    "openai_sdk_proxy_smoke_latest.md",
    "router_offline_smoke_latest.md",
    "environment_latest.md",
    "readiness_latest.md",
]

SIGNED_URL_PATTERN = "X-Amz-" + "Signature=|download_url" + r"\?"

SECRET_PATTERNS = [
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{30,}")),
    ("openai_api_key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}")),
    ("openai_admin_key", re.compile(r"ek_[A-Za-z0-9_-]{20,}")),
    ("session_token", re.compile(r"session-[A-Za-z0-9_-]{30,}")),
    ("json_access_token", re.compile(r"""["']access_token["']\s*:\s*["'][^"']{20,}["']""", re.IGNORECASE)),
    ("json_refresh_token", re.compile(r"""["']refresh_token["']\s*:\s*["'][^"']{20,}["']""", re.IGNORECASE)),
    ("signed_url", re.compile(f"({SIGNED_URL_PATTERN})", re.IGNORECASE)),
]


def run_command(name: str, command: list[str]) -> Dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("PYTHONPYCACHEPREFIX", str(ROOT / ".pycache"))
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {
        "name": name,
        "status": "pass" if proc.returncode == 0 else "fail",
        "returncode": proc.returncode,
        "output": proc.stdout.strip()[-4000:],
    }


def text_files() -> list[Path]:
    paths: list[Path] = []
    for path in ROOT.rglob("*"):
        if path.is_dir() or any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        paths.append(path)
    return sorted(paths)


def secret_scan() -> Dict[str, Any]:
    hits = []
    checked = 0
    for path in text_files():
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue
        checked += 1
        for lineno, line in enumerate(text.splitlines(), 1):
            for name, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    hits.append({
                        "path": str(path.relative_to(ROOT)),
                        "line": lineno,
                        "pattern": name,
                        "excerpt": line[:180],
                    })
    return {
        "name": "secret_scan",
        "status": "fail" if hits else "pass",
        "checked_files": checked,
        "hits": hits,
    }


def report_presence() -> Dict[str, Any]:
    missing = [name for name in REQUIRED_REPORTS if not (REPORTS / name).exists()]
    return {
        "name": "report_presence",
        "status": "fail" if missing else "pass",
        "required": REQUIRED_REPORTS,
        "missing": missing,
    }


def git_status() -> Dict[str, Any]:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {
        "name": "git_status",
        "status": "info",
        "output": proc.stdout.strip(),
    }


def with_no_write(command: list[str], no_write: bool) -> list[str]:
    if no_write:
        return [*command, "--no-write"]
    return command


def build_report(no_write: bool = False) -> Dict[str, Any]:
    checks = [
        run_command("compileall", [sys.executable, "-m", "compileall", "bridge.py", "setup_oauth.py", "src"]),
        run_command("environment_probe", with_no_write([sys.executable, "src/environment_probe.py"], no_write)),
        run_command("offline_router_smoke", with_no_write([sys.executable, "src/run_router_offline_smoke.py"], no_write)),
        run_command("route_manifest", [sys.executable, "src/verify_route_manifest.py"]),
        run_command("surface_audit", with_no_write([sys.executable, "src/audit_openai_surface.py"], no_write)),
        run_command("compatibility_guide", with_no_write([sys.executable, "src/generate_compatibility_guide.py"], no_write)),
        run_command("coverage_map", with_no_write([sys.executable, "src/generate_coverage_map.py"], no_write)),
        run_command("route_policy", with_no_write([sys.executable, "src/generate_route_policy.py"], no_write)),
        run_command("boundary_playbook", with_no_write([sys.executable, "src/generate_boundary_playbook.py"], no_write)),
        run_command("client_config", with_no_write([sys.executable, "src/generate_client_config.py"], no_write)),
        run_command("quickstart", with_no_write([sys.executable, "src/generate_quickstart.py"], no_write)),
        run_command("platform_fallback", with_no_write([sys.executable, "src/platform_fallback_status.py"], no_write)),
        run_command("goal_audit", with_no_write([sys.executable, "src/goal_audit_report.py"], no_write)),
        run_command("publish_check", with_no_write([sys.executable, "src/publish_check.py"], no_write)),
        run_command("summary_counts", with_no_write([sys.executable, "src/verify_summary_counts.py"], no_write)),
        run_command("usage_scanner_coverage", with_no_write([sys.executable, "src/verify_usage_scanner.py"], no_write)),
        run_command("status_report", with_no_write([sys.executable, "src/status_report.py", "--no-refresh-env"], no_write)),
        run_command(
            "usage_check",
            with_no_write([
                sys.executable,
                "src/check_openai_usage.py",
                "/v1/embeddings",
                "/v1/assistants",
                "/v1/videos/edits",
                "/v1/fine_tuning/jobs/ftjob_123/cancel",
            ], no_write),
        ),
        run_command(
            "migration_plan",
            with_no_write([
                sys.executable,
                "src/generate_migration_plan.py",
                "/v1/embeddings",
                "/v1/assistants",
                "/v1/videos/edits",
                "/v1/fine_tuning/jobs/ftjob_123/cancel",
            ], no_write),
        ),
        run_command("readiness_report", with_no_write([sys.executable, "src/readiness_report.py"], no_write)),
        run_command("doctor_report", with_no_write([sys.executable, "src/doctor_report.py"], no_write)),
        run_command("classify_direct_oauth", [sys.executable, "src/classify_openai_path.py", "/v1/embeddings"]),
        run_command("classify_local_compat", [sys.executable, "src/classify_openai_path.py", "/v1/assistants"]),
        run_command("classify_legacy_completions", [sys.executable, "src/classify_openai_path.py", "/v1/completions"]),
        run_command("classify_local_token_estimate", [sys.executable, "src/classify_openai_path.py", "/v1/responses/input_tokens"]),
        run_command("classify_local_compact", [sys.executable, "src/classify_openai_path.py", "/v1/responses/compact"]),
        run_command("classify_video_local", [sys.executable, "src/classify_openai_path.py", "/v1/videos/edits"]),
        run_command("classify_template_local", [sys.executable, "src/classify_openai_path.py", "/v1/videos/video_123/remix"]),
        run_command("git_diff_check", ["git", "diff", "--check"]),
        report_presence(),
        secret_scan(),
        git_status(),
    ]
    blocking = [check for check in checks if check["status"] == "fail"]
    return {
        "ok": not blocking,
        "checks": checks,
    }


def print_human(report: Dict[str, Any]) -> None:
    print("Release preflight:", "pass" if report["ok"] else "fail")
    for check in report["checks"]:
        status = check["status"]
        print(f"- {status}: {check['name']}")
        if check["name"] == "secret_scan":
            print(f"  checked_files={check['checked_files']}")
            for hit in check["hits"][:20]:
                print(f"  {hit['path']}:{hit['line']} {hit['pattern']}: {hit['excerpt']}")
        elif check["name"] == "report_presence" and check["missing"]:
            print("  missing=" + ", ".join(check["missing"]))
        elif check.get("output") and status == "fail":
            print("  " + str(check["output"]).replace("\n", "\n  "))
        elif check["name"] == "git_status" and check.get("output"):
            print("  " + str(check["output"]).replace("\n", "\n  "))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local preflight checks before publishing OAuth bridge changes.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--no-write", action="store_true", help="Do not refresh generated reports while running checks.")
    args = parser.parse_args()

    report = build_report(no_write=args.no_write)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
