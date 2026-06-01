from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from generate_compatibility_guide import build_report as build_compatibility_guide_report
from platform_fallback import API_KEY_ENV, ENABLE_ENV, MODE_ENV
from readiness_report import build_report as build_readiness_report


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
PLACEHOLDER_API_KEY = "oauth-local-proxy"


def normalize_base_url(host: str, port: int, base_url: Optional[str] = None) -> str:
    if base_url:
        value = base_url.rstrip("/")
        return value if value.endswith("/v1") else f"{value}/v1"
    return f"http://{host}:{port}/v1"


def build_report(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_base_url = normalize_base_url(host, port, base_url)
    guide = build_compatibility_guide_report()
    readiness = build_readiness_report()
    category_counts = guide.get("category_counts", {})

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_url": resolved_base_url,
        "host": host,
        "port": port,
        "placeholder_api_key": PLACEHOLDER_API_KEY,
        "goal_complete": readiness.get("goal_complete"),
        "bottom_line": readiness.get("bottom_line"),
        "category_counts": category_counts,
        "environment": {
            "OPENAI_BASE_URL": resolved_base_url,
            "OPENAI_API_KEY": PLACEHOLDER_API_KEY,
        },
        "commands": {
            "start_proxy": f"python bridge.py serve --host {host} --port {port}",
            "quickstart": "python bridge.py quickstart",
            "live_check": "python bridge.py live-check",
            "publish_check": "python bridge.py publish-check",
            "publish_api": "python bridge.py publish-api --dry-run",
            "publish_gate": "bash reports/openai_bridge_publish_gate.sh --push",
            "finish_gate": "bash reports/openai_bridge_finish_gate.sh --push",
            "status": "python bridge.py status",
            "verdict": "python bridge.py verdict",
            "strict_verdict": "python bridge.py verdict --strict",
            "doctor": "python bridge.py doctor",
            "readiness": "python bridge.py readiness",
            "guide": "python bridge.py guide",
            "coverage": "python bridge.py coverage",
            "fallback": "python bridge.py fallback",
            "enable_boundary_fallback": f"export {ENABLE_ENV}=1 {MODE_ENV}=boundary {API_KEY_ENV}=sk-...",
            "enable_prefer_platform": f"export {ENABLE_ENV}=1 {MODE_ENV}=prefer {API_KEY_ENV}=sk-...",
            "check_app": "python bridge.py check path/to/your/app --fail-on-boundary",
            "migration_plan": "python bridge.py migrate path/to/your/app --fail-on-boundary",
        },
        "metadata_endpoints": {
            "health": resolved_base_url.replace("/v1", "/health"),
            "capabilities": f"{resolved_base_url}/oauth-capabilities",
            "readiness": f"{resolved_base_url}/oauth-readiness",
            "compatibility_guide": f"{resolved_base_url}/oauth-compatibility-guide",
            "quickstart": f"{resolved_base_url}/oauth-quickstart",
            "coverage_map": f"{resolved_base_url}/oauth-coverage-map",
            "route_policy": f"{resolved_base_url}/oauth-route-policy",
            "status": f"{resolved_base_url}/oauth-status",
            "goal_audit": f"{resolved_base_url}/oauth-goal-audit",
            "classify_embeddings": f"{resolved_base_url}/oauth-classify?path=/v1/embeddings",
            "client_config": f"{resolved_base_url}/oauth-client-config",
        },
        "generated_files": {
            "env_example": "reports/openai_bridge.env.example",
            "ci_gate": "reports/openai_bridge_ci_gate.sh",
            "launch_gate": "reports/openai_bridge_launch_gate.sh",
            "publish_gate": "reports/openai_bridge_publish_gate.sh",
            "finish_gate": "reports/openai_bridge_finish_gate.sh",
        },
        "python_sdk": {
            "install": "pip install openai",
            "code": "\n".join([
                "from openai import OpenAI",
                "",
                "client = OpenAI(",
                f"    api_key=\"{PLACEHOLDER_API_KEY}\",",
                f"    base_url=\"{resolved_base_url}\",",
                ")",
                "",
                "response = client.responses.create(",
                "    model=\"gpt-5.5\",",
                "    input=\"Reply exactly: bridge ready\",",
                ")",
                "print(response.output_text)",
            ]),
        },
        "javascript_sdk": {
            "install": "npm install openai",
            "code": "\n".join([
                "import OpenAI from \"openai\";",
                "",
                "const client = new OpenAI({",
                f"  apiKey: \"{PLACEHOLDER_API_KEY}\",",
                f"  baseURL: \"{resolved_base_url}\",",
                "});",
                "",
                "const response = await client.responses.create({",
                "  model: \"gpt-5.5\",",
                "  input: \"Reply exactly: bridge ready\",",
                "});",
                "console.log(response.output_text);",
            ]),
        },
        "curl": {
            "health": f"curl -s {resolved_base_url.replace('/v1', '/health')}",
            "classify": f"curl -s '{resolved_base_url}/oauth-classify?path=/v1/embeddings'",
            "response": " ".join([
                "curl -s",
                f"{resolved_base_url}/responses",
                "-H 'Content-Type: application/json'",
                f"-H 'Authorization: Bearer {PLACEHOLDER_API_KEY}'",
                "-d '{\"model\":\"gpt-5.5\",\"input\":\"Reply exactly: bridge ready\"}'",
            ]),
        },
        "warnings": [
            "This base_url points to the local bridge, not hosted https://api.openai.com/v1.",
            "Use bridge.py check before migrating an app; any route reported as an API/Admin-key boundary must stay disabled or use official Platform credentials.",
            "Use bridge.py migrate for a paste-ready migration plan with base_url, SDK key, CI gate, and blocked route list.",
            "Use bridge.py coverage for a product-group view of direct OAuth, local bridge, and Platform-credential boundaries.",
            "The placeholder API key is only for SDK clients that require a non-empty key; the local proxy uses the local ChatGPT/Codex OAuth session.",
            "Run bridge.py live-check from a normal local shell before making launch-ready claims.",
            "Run bridge.py publish-check before claiming GitHub or clone users have the latest bridge.",
            "Use bridge.py publish-api --dry-run to validate the GitHub API publish fallback before using it with GITHUB_TOKEN or GH_TOKEN.",
            "Use reports/openai_bridge_publish_gate.sh --push from a normal networked shell to run no-write preflight, push the current branch, refresh origin, and re-check publish state.",
            "Use reports/openai_bridge_finish_gate.sh --push from a normal networked shell to run publish and live launch gates in order.",
            "Run bridge.py readiness before claiming the whole OpenAI API surface is available through OAuth.",
            "Set OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1 plus OPENAI_API_KEY, OPENAI_ACCESS_TOKEN, or OPENAI_ADMIN_KEY only when you intentionally want the local proxy to forward requests to the official Platform API.",
            "Default fallback mode is boundary. Set OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=prefer only when you want hosted OpenAI API behavior to take precedence over local compatibility handlers.",
        ],
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "client_config_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    (REPORTS / "openai_bridge.env.example").write_text("\n".join([
        "# Local ChatGPT/Codex OAuth bridge client environment",
        f"OPENAI_BASE_URL={payload['environment']['OPENAI_BASE_URL']}",
        f"OPENAI_API_KEY={payload['environment']['OPENAI_API_KEY']}",
        "",
        "# Optional hybrid Platform fallback. Leave disabled for OAuth-only mode.",
        "# OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1",
        "# OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=boundary",
        "# OPENAI_API_KEY=sk-...",
        "# OPENAI_ADMIN_KEY=sk-admin-or-ek-...",
        "# OPENAI_ACCESS_TOKEN=official-workload-identity-bearer",
        "",
        "# Optional Realtime model overrides. The defaults preserve the latest local",
        "# OAuth matrix proof; the comments show current guide-oriented choices.",
        "# OAUTH_BRIDGE_REALTIME_MODEL=gpt-realtime-2",
        "# OAUTH_BRIDGE_REALTIME_TRANSCRIPTION_MODEL=gpt-realtime-whisper",
        "# OAUTH_BRIDGE_REALTIME_TRANSLATION_MODEL=gpt-realtime-translate",
        "# OAUTH_BRIDGE_REALTIME_TRANSLATION_TRANSCRIPTION_MODEL=gpt-realtime-whisper",
        "",
    ]))
    (REPORTS / "openai_bridge_ci_gate.sh").write_text("\n".join([
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "PYTHON_BIN=\"${PYTHON:-python3}\"",
        "",
        "# Package/report and route-policy gate. This does not prove live launch readiness.",
        "\"$PYTHON_BIN\" bridge.py preflight",
        "\"$PYTHON_BIN\" bridge.py verdict",
        "# For a failing go/no-go exit code, use: \"$PYTHON_BIN\" bridge.py verdict --strict",
        "",
        "if [ \"$#\" -eq 0 ]; then",
        "  echo \"usage: reports/openai_bridge_ci_gate.sh path/to/app-or-file [more paths...]\" >&2",
        "  exit 2",
        "fi",
        "",
        "\"$PYTHON_BIN\" bridge.py check \"$@\" --fail-on-boundary",
        "",
    ]))
    (REPORTS / "openai_bridge_launch_gate.sh").write_text("\n".join([
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "PYTHON_BIN=\"${PYTHON:-python3}\"",
        "",
        "# Live launch gate. Run from a normal local shell with network and localhost bind access.",
        "\"$PYTHON_BIN\" bridge.py live-check \"$@\"",
        "",
    ]))
    (REPORTS / "openai_bridge_publish_gate.sh").write_text("\n".join([
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "PYTHON_BIN=\"${PYTHON:-python3}\"",
        "",
        "# Publish gate. Run from a normal shell with GitHub network access.",
        "# Use --push to push the current branch before the strict publish check.",
        "# This gate is no-write so a committed tree stays clean while it runs.",
        "\"$PYTHON_BIN\" bridge.py preflight --no-write",
        "",
        "if [ \"${1:-}\" = \"--push\" ]; then",
        "  branch=\"$(git branch --show-current)\"",
        "  if [ -z \"$branch\" ]; then",
        "    echo \"Could not determine current git branch.\" >&2",
        "    exit 2",
        "  fi",
        "  if ! git push origin \"$branch\"; then",
        "    if [ -n \"${GITHUB_TOKEN:-${GH_TOKEN:-}}\" ]; then",
        "      echo \"git push failed; trying GitHub API publish fallback with GITHUB_TOKEN/GH_TOKEN.\" >&2",
        "      \"$PYTHON_BIN\" bridge.py publish-api --branch \"$branch\"",
        "    else",
        "      echo \"git push failed and no GITHUB_TOKEN or GH_TOKEN is set for the API fallback.\" >&2",
        "      echo \"Run from a shell that can resolve github.com, or set GITHUB_TOKEN/GH_TOKEN and retry.\" >&2",
        "      exit 1",
        "    fi",
        "  fi",
        "  git fetch origin \"refs/heads/$branch:refs/remotes/origin/$branch\"",
        "fi",
        "",
        "\"$PYTHON_BIN\" bridge.py publish-check --no-write --strict",
        "",
    ]))
    (REPORTS / "openai_bridge_finish_gate.sh").write_text("\n".join([
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# End-to-end gate. Run from a normal shell with GitHub network access,",
        "# ChatGPT/Codex network access, and localhost bind permission.",
        "publish_args=()",
        "if [ \"${1:-}\" = \"--push\" ]; then",
        "  publish_args=(--push)",
        "  shift",
        "fi",
        "",
        "bash reports/openai_bridge_publish_gate.sh \"${publish_args[@]}\"",
        "bash reports/openai_bridge_launch_gate.sh \"$@\"",
        "",
    ]))

    lines = [
        "# OAuth Bridge Client Config",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Base URL: `{payload['base_url']}`",
        f"- Placeholder API key: `{payload['placeholder_api_key']}`",
        f"- Goal complete: `{payload['goal_complete']}`",
        f"- Bottom line: {payload['bottom_line']}",
        f"- Env example: `{payload['generated_files']['env_example']}`",
        f"- CI gate: `{payload['generated_files']['ci_gate']}`",
        f"- Launch gate: `{payload['generated_files']['launch_gate']}`",
        f"- Publish gate: `{payload['generated_files']['publish_gate']}`",
        f"- Finish gate: `{payload['generated_files']['finish_gate']}`",
        "",
        "## Category Counts",
        "",
        "| Category | Paths |",
        "|---|---:|",
    ]
    for category, count in sorted(payload["category_counts"].items()):
        lines.append(f"| `{category}` | {count} |")

    lines.extend([
        "",
        "## Start The Proxy",
        "",
        "```bash",
        payload["commands"]["start_proxy"],
        "```",
        "",
        "## Environment Variables",
        "",
        "```bash",
        f"export OPENAI_BASE_URL={payload['environment']['OPENAI_BASE_URL']}",
        f"export OPENAI_API_KEY={payload['environment']['OPENAI_API_KEY']}",
        "```",
        "",
        "## Optional Platform Fallback",
        "",
        "```bash",
        payload["commands"]["enable_boundary_fallback"],
        "# exact hosted API behavior before local compatibility handlers:",
        payload["commands"]["enable_prefer_platform"],
        "```",
        "",
        "## Python SDK",
        "",
        "```python",
        payload["python_sdk"]["code"],
        "```",
        "",
        "## JavaScript SDK",
        "",
        "```js",
        payload["javascript_sdk"]["code"],
        "```",
        "",
        "## cURL",
        "",
        "```bash",
        payload["curl"]["health"],
        payload["curl"]["classify"],
        payload["curl"]["response"],
        "```",
        "",
        "## Metadata Endpoints",
        "",
        "| Name | URL |",
        "|---|---|",
    ])
    for name, url in payload["metadata_endpoints"].items():
        lines.append(f"| `{name}` | `{url}` |")

    lines.extend([
        "",
        "## Warnings",
        "",
    ])
    for warning in payload["warnings"]:
        lines.append(f"- {warning}")
    lines.append("")
    (REPORTS / "client_config_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any]) -> None:
    print("OAuth bridge client config")
    print(f"base_url={payload['base_url']}")
    print(f"placeholder_api_key={payload['placeholder_api_key']}")
    print(f"goal_complete={payload['goal_complete']}")
    print(payload["bottom_line"])
    print()
    print("Start:")
    print(f"  {payload['commands']['start_proxy']}")
    print("Python SDK:")
    print(f"  client = OpenAI(api_key=\"{payload['placeholder_api_key']}\", base_url=\"{payload['base_url']}\")")
    print("JavaScript SDK:")
    print(f"  const client = new OpenAI({{ apiKey: \"{payload['placeholder_api_key']}\", baseURL: \"{payload['base_url']}\" }});")
    print()
    print("Before migrating an app:")
    print(f"  {payload['commands']['check_app']}")
    print(f"  {payload['commands']['migration_plan']}")
    print("Launch gate:")
    print(f"  {payload['commands']['live_check']}")
    print("Publish gate:")
    print(f"  {payload['commands']['publish_gate']}")
    print("Finish gate:")
    print(f"  {payload['commands']['finish_gate']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SDK/curl configuration for the local OAuth bridge.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--base-url", help="Override the printed base URL.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/client_config_latest.*.")
    args = parser.parse_args()

    payload = build_report(host=args.host, port=args.port, base_url=args.base_url)
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
