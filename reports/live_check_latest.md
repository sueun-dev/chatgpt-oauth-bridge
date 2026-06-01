# OAuth Bridge Live Launch Check

- Generated: `2026-06-01T17:48:39Z`
- OK: `False`
- Bottom line: Live launch check did not pass. See failed or skipped checks before making launch-ready claims.
- Host: `127.0.0.1`
- Port: `0`
- Include images: `False`
- Skip speech: `False`

## Environment

| Check | OK | Evidence |
|---|---|---|
| Token source | `True` | `source=codex-cli; error=None` |
| Codex model discovery | `False` | `http_status=None; model_count=None; error=[Errno 8] nodename nor servname provided, or not known` |
| Localhost bind | `False` | `host=127.0.0.1; port=0; error=[Errno 1] Operation not permitted` |

## Checks

| Status | Check | Return Code | Command | Evidence |
|---|---|---:|---|---|
| `fail` | `environment_probe` | `1` | `/Users/sueuncho/Documents/openao-oauth-access/.venv/bin/python src/environment_probe.py --host 127.0.0.1 --port 0 --timeout 5.0` | token_source_ok=True; codex_model_discovery_ok=False; codex_model_discovery_error_type=ConnectError; localhost_bind_ok=False; localhost_bind_error_type=PermissionError |
| `skipped` | `http_proxy_smoke` | `None` | `None` | Skipped because current environment cannot prove Codex model discovery and localhost bind. |
| `skipped` | `openai_python_sdk_smoke` | `None` | `None` | Skipped because current environment cannot prove Codex model discovery and localhost bind. |
| `pass` | `readiness_report` | `0` | `/Users/sueuncho/Documents/openao-oauth-access/.venv/bin/python src/readiness_report.py` | OAuth bridge readiness: not complete Not complete: every documented path is mapped to direct OAuth or explicit local compatibility, but only 5 paths are direct hosted OAuth and this environment cannot prove live Codex network access and localhost SDK smoke.  - met: Documented OpenAI API surface has direct OAuth proof or explicit local/ChatGPT compatibility coverage   official_paths=172; direct_oauth=5; local_bridge=167; api_key_or_admin_key_required=0; incomplete_or_resource_bound=0 - met: Legal |
| `fail` | `doctor_strict` | `1` | `/Users/sueuncho/Documents/openao-oauth-access/.venv/bin/python src/doctor_report.py --strict` | OAuth bridge doctor: strict-fail Package health checks pass, but the current environment cannot prove the full goal.  state=package_health_ok=True; local_router_ok=True; live_environment_ok=False; full_goal_complete=False coverage=official_paths=172; direct_oauth=5; local_bridge=167; platform_boundary=0 environment=codex_model_discovery_ok=False; localhost_bind_ok=False platform_fallback=enabled=False; mode=boundary; api_key_present=False; access_token_present=False; admin_key_present=False  War |

## Next Actions

- DNS/network is blocked in this shell; run from a shell that can resolve chatgpt.com, github.com, and api.openai.com.
- This shell denies socket bind with PermissionError; use a normal local shell for live HTTP/SDK smoke.
- Inspect doctor_strict output in reports/live_check_latest.md and rerun after fixing it.
