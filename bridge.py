from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"


def script_python() -> str:
    override = os.environ.get("OAUTH_BRIDGE_PYTHON")
    if override:
        return override
    if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
        return str(VENV_PYTHON)
    return sys.executable


def child_env() -> dict[str, str]:
    env = os.environ.copy()
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC) if not current else f"{SRC}{os.pathsep}{current}"
    env.setdefault("PYTHONPYCACHEPREFIX", str(ROOT / ".pycache"))
    return env


def run_script(script: str, args: list[str]) -> int:
    command = [script_python(), str(ROOT / script), *args]
    return subprocess.run(command, cwd=ROOT, env=child_env(), check=False).returncode


def cmd_setup(args: argparse.Namespace) -> int:
    script_args = ["--no-smoke"] if args.no_smoke else []
    return run_script("setup_oauth.py", script_args)


def cmd_info(args: argparse.Namespace) -> int:
    return run_script("src/openai_oauth_access.py", [])


def cmd_serve(args: argparse.Namespace) -> int:
    script_args = ["--host", args.host, "--port", str(args.port)]
    return run_script("src/oauth_openai_compat_server.py", script_args)


def cmd_smoke(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.include_images:
        script_args.append("--include-images")
    if args.skip_speech:
        script_args.append("--skip-speech")
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/run_proxy_smoke.py", script_args)


def cmd_sdk_smoke(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.include_images:
        script_args.append("--include-images")
    if args.skip_speech:
        script_args.append("--skip-speech")
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/run_openai_sdk_proxy_smoke.py", script_args)


def cmd_offline_smoke(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/run_router_offline_smoke.py", script_args)


def cmd_readiness(args: argparse.Namespace) -> int:
    script_args = ["--json"] if args.json else []
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/readiness_report.py", script_args)


def cmd_env(args: argparse.Namespace) -> int:
    script_args = ["--host", args.host, "--port", str(args.port), "--timeout", str(args.timeout)]
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/environment_probe.py", script_args)


def cmd_classify(args: argparse.Namespace) -> int:
    script_args = [args.path]
    if args.json:
        script_args.append("--json")
    return run_script("src/classify_openai_path.py", script_args)


def cmd_guide(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.category:
        script_args.extend(["--category", args.category])
    if args.limit is not None:
        script_args.extend(["--limit", str(args.limit)])
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/generate_compatibility_guide.py", script_args)


def cmd_config(args: argparse.Namespace) -> int:
    script_args = ["--host", args.host, "--port", str(args.port)]
    if args.base_url:
        script_args.extend(["--base-url", args.base_url])
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/generate_client_config.py", script_args)


def cmd_quickstart(args: argparse.Namespace) -> int:
    script_args = ["--host", args.host, "--port", str(args.port)]
    if args.base_url:
        script_args.extend(["--base-url", args.base_url])
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/generate_quickstart.py", script_args)


def cmd_coverage(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.group:
        script_args.extend(["--group", args.group])
    if args.limit is not None:
        script_args.extend(["--limit", str(args.limit)])
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/generate_coverage_map.py", script_args)


def cmd_fallback(args: argparse.Namespace) -> int:
    script_args = list(args.paths)
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/platform_fallback_status.py", script_args)


def cmd_policy(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.json:
        script_args.append("--json")
    if args.limit is not None:
        script_args.extend(["--limit", str(args.limit)])
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/generate_route_policy.py", script_args)


def cmd_boundaries(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.limit is not None:
        script_args.extend(["--limit", str(args.limit)])
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/generate_boundary_playbook.py", script_args)


def cmd_status(args: argparse.Namespace) -> int:
    script_args = ["--host", args.host, "--port", str(args.port), "--timeout", str(args.timeout)]
    if args.no_refresh_env:
        script_args.append("--no-refresh-env")
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/status_report.py", script_args)


def cmd_verdict(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    if args.strict:
        script_args.append("--strict")
    return run_script("src/goal_audit_report.py", script_args)


def cmd_check(args: argparse.Namespace) -> int:
    script_args = list(args.items)
    if args.limit is not None:
        script_args.extend(["--limit", str(args.limit)])
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    if args.fail_on_boundary:
        script_args.append("--fail-on-boundary")
    return run_script("src/check_openai_usage.py", script_args)


def cmd_migrate(args: argparse.Namespace) -> int:
    script_args = list(args.items)
    script_args.extend(["--host", args.host, "--port", str(args.port)])
    if args.base_url:
        script_args.extend(["--base-url", args.base_url])
    if args.limit is not None:
        script_args.extend(["--limit", str(args.limit)])
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    if args.fail_on_boundary:
        script_args.append("--fail-on-boundary")
    return run_script("src/generate_migration_plan.py", script_args)


def cmd_audit(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.no_existing_fallback:
        script_args.append("--no-existing-fallback")
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/audit_openai_surface.py", script_args)


def cmd_preflight(args: argparse.Namespace) -> int:
    script_args = ["--json"] if args.json else []
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/release_preflight.py", script_args)


def cmd_publish_check(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    if args.strict:
        script_args.append("--strict")
    return run_script("src/publish_check.py", script_args)


def cmd_publish_api(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.repo:
        script_args.extend(["--repo", args.repo])
    if args.branch:
        script_args.extend(["--branch", args.branch])
    if args.dry_run:
        script_args.append("--dry-run")
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/github_api_publish.py", script_args)


def cmd_live_check(args: argparse.Namespace) -> int:
    script_args = ["--host", args.host, "--port", str(args.port), "--timeout", str(args.timeout)]
    if args.include_images:
        script_args.append("--include-images")
    if args.skip_speech:
        script_args.append("--skip-speech")
    if args.force:
        script_args.append("--force")
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    return run_script("src/live_launch_check.py", script_args)


def cmd_finish(args: argparse.Namespace) -> int:
    command = ["bash", str(ROOT / "reports" / "openai_bridge_finish_gate.sh")]
    if args.push:
        command.append("--push")
    if args.include_images:
        command.append("--include-images")
    if args.skip_speech:
        command.append("--skip-speech")
    if args.force:
        command.append("--force")
    return subprocess.run(command, cwd=ROOT, env=child_env(), check=False).returncode


def cmd_doctor(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.json:
        script_args.append("--json")
    if args.no_write:
        script_args.append("--no-write")
    if args.strict:
        script_args.append("--strict")
    return run_script("src/doctor_report.py", script_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="One-command entrypoint for ChatGPT OAuth Bridge setup, serving, and verification.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup = subparsers.add_parser("setup", help="Check local Codex/ChatGPT OAuth readiness.")
    setup.add_argument("--no-smoke", action="store_true", help="Skip the tiny text generation smoke.")
    setup.set_defaults(func=cmd_setup)

    info = subparsers.add_parser("info", help="Print selected OAuth source, models, and wrapper method names.")
    info.set_defaults(func=cmd_info)

    serve = subparsers.add_parser("serve", help="Run the local OpenAI-compatible /v1 proxy.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    serve.set_defaults(func=cmd_serve)

    smoke = subparsers.add_parser("smoke", help="Run HTTP smoke tests against an ephemeral local proxy.")
    smoke.add_argument("--include-images", action="store_true", help="Also verify image generation.")
    smoke.add_argument("--skip-speech", action="store_true", help="Skip Realtime PCM16 speech.")
    smoke.add_argument("--no-write", action="store_true", help="Do not write reports/proxy_smoke_latest.*.")
    smoke.set_defaults(func=cmd_smoke)

    sdk_smoke = subparsers.add_parser("sdk-smoke", help="Run official OpenAI Python SDK smoke tests against the local proxy.")
    sdk_smoke.add_argument("--include-images", action="store_true", help="Also verify image generation.")
    sdk_smoke.add_argument("--skip-speech", action="store_true", help="Skip Realtime PCM16 speech.")
    sdk_smoke.add_argument("--no-write", action="store_true", help="Do not write reports/openai_sdk_proxy_smoke_latest.*.")
    sdk_smoke.set_defaults(func=cmd_sdk_smoke)

    offline_smoke = subparsers.add_parser(
        "offline-smoke",
        help="Run no-network, no-socket checks for local router compatibility logic.",
    )
    offline_smoke.add_argument("--no-write", action="store_true", help="Do not write reports/router_offline_smoke_latest.*.")
    offline_smoke.set_defaults(func=cmd_offline_smoke)

    readiness = subparsers.add_parser("readiness", help="Summarize whether the full OAuth bridge goal is currently achieved.")
    readiness.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    readiness.add_argument("--no-write", action="store_true", help="Do not write reports/readiness_latest.*.")
    readiness.set_defaults(func=cmd_readiness)

    env = subparsers.add_parser("env", help="Probe current token, network, and localhost bind environment.")
    env.add_argument("--host", default="127.0.0.1")
    env.add_argument("--port", type=int, default=0)
    env.add_argument("--timeout", type=float, default=5.0)
    env.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    env.add_argument("--no-write", action="store_true", help="Do not write reports/environment_latest.*.")
    env.set_defaults(func=cmd_env)

    classify = subparsers.add_parser("classify", help="Classify one OpenAI API path using the latest OAuth surface audit.")
    classify.add_argument("path", help="Path such as /v1/responses, /embeddings, or a full api.openai.com URL.")
    classify.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    classify.set_defaults(func=cmd_classify)

    guide = subparsers.add_parser("guide", help="Print and write the user-facing OAuth compatibility guide.")
    guide.add_argument(
        "--category",
        choices=[
            "api_key_or_admin_key_required",
            "direct_official_oauth_verified",
            "local_compat_or_chatgpt_backend_bridge",
            "not_available_current_deployment",
            "not_probed_directly",
            "official_route_auth_reached_but_not_complete",
            "resource_bound_not_fully_verified",
        ],
        help="Show only one category.",
    )
    guide.add_argument("--limit", type=int, default=8, help="Number of paths to print per category.")
    guide.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    guide.add_argument("--no-write", action="store_true", help="Do not write reports/compatibility_guide_latest.*.")
    guide.set_defaults(func=cmd_guide)

    config = subparsers.add_parser("config", help="Print SDK, curl, and env config for local bridge clients.")
    config.add_argument("--host", default="127.0.0.1")
    config.add_argument("--port", type=int, default=8787)
    config.add_argument("--base-url", help="Override the printed base URL.")
    config.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    config.add_argument("--no-write", action="store_true", help="Do not write reports/client_config_latest.*.")
    config.set_defaults(func=cmd_config)

    quickstart = subparsers.add_parser("quickstart", help="Generate the first-run bundle for using the bridge safely.")
    quickstart.add_argument("--host", default="127.0.0.1")
    quickstart.add_argument("--port", type=int, default=8787)
    quickstart.add_argument("--base-url", help="Override the generated local bridge base URL.")
    quickstart.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    quickstart.add_argument("--no-write", action="store_true", help="Do not write reports/quickstart_latest.*.")
    quickstart.set_defaults(func=cmd_quickstart)

    coverage = subparsers.add_parser("coverage", help="Group OpenAI API coverage by product area.")
    coverage.add_argument("--group", help="Print only one product group, such as realtime or organization/admin.")
    coverage.add_argument("--limit", type=int, default=30, help="Number of groups to print.")
    coverage.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    coverage.add_argument("--no-write", action="store_true", help="Do not write reports/coverage_map_latest.*.")
    coverage.set_defaults(func=cmd_coverage)

    fallback = subparsers.add_parser("fallback", help="Show explicit Platform/Admin credential fallback state.")
    fallback.add_argument("paths", nargs="*", help="OpenAI paths to check for Platform fallback routing.")
    fallback.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    fallback.add_argument("--no-write", action="store_true", help="Do not write reports/platform_fallback_latest.*.")
    fallback.set_defaults(func=cmd_fallback)

    policy = subparsers.add_parser("policy", help="Generate machine-readable allow/deny/fallback route policy.")
    policy.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    policy.add_argument("--limit", type=int, default=20, help="Number of denied paths to print.")
    policy.add_argument("--no-write", action="store_true", help="Do not write reports/openai_bridge_route_policy.*.")
    policy.set_defaults(func=cmd_policy)

    boundaries = subparsers.add_parser("boundaries", help="Generate a safe playbook for remaining Platform/Admin boundaries.")
    boundaries.add_argument("--limit", type=int, default=20, help="Number of boundary groups to print.")
    boundaries.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    boundaries.add_argument("--no-write", action="store_true", help="Do not write reports/boundary_playbook_latest.*.")
    boundaries.set_defaults(func=cmd_boundaries)

    status = subparsers.add_parser("status", help="Print a one-screen bridge status, config, and next-action dashboard.")
    status.add_argument("--host", default="127.0.0.1")
    status.add_argument("--port", type=int, default=8787)
    status.add_argument("--timeout", type=float, default=2.0)
    status.add_argument("--no-refresh-env", action="store_true", help="Use the latest environment report instead of probing now.")
    status.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    status.add_argument("--no-write", action="store_true", help="Do not write reports/status_latest.* or dependency reports.")
    status.set_defaults(func=cmd_status)

    verdict = subparsers.add_parser(
        "verdict",
        help="Audit the bridge against the full goal: complete API support, safe workarounds, and user readiness.",
    )
    verdict.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    verdict.add_argument("--no-write", action="store_true", help="Do not write reports/goal_audit_latest.*.")
    verdict.add_argument("--strict", action="store_true", help="Exit non-zero unless the full-goal verdict is complete.")
    verdict.set_defaults(func=cmd_verdict)

    check = subparsers.add_parser("check", help="Check API paths or source files against the OAuth compatibility guide.")
    check.add_argument("items", nargs="+", help="OpenAI API paths, full URLs, files, or directories to scan.")
    check.add_argument("--limit", type=int, default=20, help="Number of findings to print.")
    check.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    check.add_argument("--no-write", action="store_true", help="Do not write reports/usage_check_latest.*.")
    check.add_argument("--fail-on-boundary", action="store_true", help="Exit non-zero when blocked or unproven paths are found.")
    check.set_defaults(func=cmd_check)

    migrate = subparsers.add_parser("migrate", help="Generate an app migration plan for the local OAuth bridge.")
    migrate.add_argument("items", nargs="+", help="OpenAI API paths, full URLs, files, or directories to scan.")
    migrate.add_argument("--host", default="127.0.0.1")
    migrate.add_argument("--port", type=int, default=8787)
    migrate.add_argument("--base-url", help="Override the generated local bridge base URL.")
    migrate.add_argument("--limit", type=int, default=20, help="Number of blocked findings to print.")
    migrate.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    migrate.add_argument("--no-write", action="store_true", help="Do not write reports/migration_plan_latest.*.")
    migrate.add_argument("--fail-on-boundary", action="store_true", help="Exit non-zero when blocked or unproven paths are found.")
    migrate.set_defaults(func=cmd_migrate)

    audit = subparsers.add_parser("audit", help="Refresh the official OpenAI API surface audit.")
    audit.add_argument(
        "--no-existing-fallback",
        action="store_true",
        help="Fail if the OpenAPI source cannot be fetched instead of reusing the latest checked-in path list.",
    )
    audit.add_argument("--no-write", action="store_true", help="Do not write reports/openai_surface_audit_latest.*.")
    audit.set_defaults(func=cmd_audit)

    preflight = subparsers.add_parser("preflight", help="Run compile, whitespace, report, and secret checks.")
    preflight.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    preflight.add_argument("--no-write", action="store_true", help="Do not refresh generated reports while running checks.")
    preflight.set_defaults(func=cmd_preflight)

    publish_check = subparsers.add_parser("publish-check", help="Check whether local changes are committed and published to GitHub.")
    publish_check.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    publish_check.add_argument("--no-write", action="store_true", help="Do not write reports/publish_check_latest.*.")
    publish_check.add_argument("--strict", action="store_true", help="Exit non-zero unless local HEAD matches the upstream branch.")
    publish_check.set_defaults(func=cmd_publish_check)

    publish_api = subparsers.add_parser("publish-api", help="Publish clean local HEAD to GitHub using GITHUB_TOKEN/GH_TOKEN and the Git data API.")
    publish_api.add_argument("--repo", help="Repository in owner/name form. Defaults to parsing origin.")
    publish_api.add_argument("--branch", help="Branch to update. Defaults to the current branch.")
    publish_api.add_argument("--dry-run", action="store_true", help="Validate and list changed paths without writing to GitHub.")
    publish_api.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    publish_api.add_argument("--no-write", action="store_true", help="Do not write reports/github_api_publish_plan_latest.*.")
    publish_api.set_defaults(func=cmd_publish_api)

    live_check = subparsers.add_parser(
        "live-check",
        help="Run the launch gate: environment, HTTP proxy smoke, SDK smoke, readiness, and strict doctor.",
    )
    live_check.add_argument("--host", default="127.0.0.1")
    live_check.add_argument("--port", type=int, default=0)
    live_check.add_argument("--timeout", type=float, default=5.0)
    live_check.add_argument("--include-images", action="store_true", help="Also verify image generation in live smokes.")
    live_check.add_argument("--skip-speech", action="store_true", help="Skip Realtime PCM16/audio speech routes.")
    live_check.add_argument("--force", action="store_true", help="Run live smokes even when the environment probe fails.")
    live_check.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    live_check.add_argument("--no-write", action="store_true", help="Do not write reports/live_check_latest.*.")
    live_check.set_defaults(func=cmd_live_check)

    finish = subparsers.add_parser(
        "finish",
        help="Run the end-to-end gate: publish-check/push first, then live launch check.",
    )
    finish.add_argument("--push", action="store_true", help="Push the current branch before strict publish-check.")
    finish.add_argument("--include-images", action="store_true", help="Also verify image generation in live smokes.")
    finish.add_argument("--skip-speech", action="store_true", help="Skip Realtime PCM16/audio speech routes.")
    finish.add_argument("--force", action="store_true", help="Run live smokes even when the environment probe fails.")
    finish.set_defaults(func=cmd_finish)

    doctor = subparsers.add_parser("doctor", help="Run package, environment, and full-goal diagnostics.")
    doctor.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    doctor.add_argument("--no-write", action="store_true", help="Do not write reports/doctor_latest.*.")
    doctor.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero unless package health, live environment, and full-goal readiness all pass.",
    )
    doctor.set_defaults(func=cmd_doctor)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
