# OAuth Bridge Live Launch Check

- Generated: `2026-06-06T13:20:39Z`
- OK: `True`
- Bottom line: Live launch check passed: environment, HTTP proxy smoke, SDK smoke, readiness, and strict doctor all passed.
- Host: `127.0.0.1`
- Port: `0`
- Include images: `True`
- Skip speech: `False`

## Environment

| Check | OK | Evidence |
|---|---|---|
| Token source | `True` | `source=codex-cli; error=None` |
| Codex model discovery | `True` | `http_status=200; model_count=5; error=None` |
| Localhost bind | `True` | `host=127.0.0.1; port=65076; error=None` |

## Checks

| Status | Check | Return Code | Command | Evidence |
|---|---|---:|---|---|
| `pass` | `environment_probe` | `0` | `/Library/Developer/CommandLineTools/usr/bin/python3 src/environment_probe.py --host 127.0.0.1 --port 0 --timeout 5.0` | token_source_ok=True; codex_model_discovery_ok=True; codex_model_discovery_error_type=None; localhost_bind_ok=True; localhost_bind_error_type=None |
| `pass` | `http_proxy_smoke` | `0` | `/Library/Developer/CommandLineTools/usr/bin/python3 src/run_proxy_smoke.py --host 127.0.0.1 --port 0 --include-images` | [pass] health [pass] capabilities [pass] cors_preflight_responses [pass] models [pass] models_retrieve [pass] assistants_create [pass] assistants_list [pass] assistants_retrieve [pass] assistants_update [pass] threads_create [pass] threads_retrieve [pass] threads_update [pass] thread_messages_create [pass] thread_messages_list [pass] thread_messages_retrieve [pass] thread_messages_update [pass] thread_runs_create [pass] thread_runs_list [pass] thread_runs_retrieve [pass] thread_runs_update [pass |
| `pass` | `openai_python_sdk_smoke` | `0` | `/Library/Developer/CommandLineTools/usr/bin/python3 src/run_openai_sdk_proxy_smoke.py --host 127.0.0.1 --port 0 --include-images` | istants API is deprecated in favor of the Responses API   response = client.beta.threads.runs.cancel(run_id, thread_id=thread_id) /Users/sueuncho/Documents/Documents_Codex/03_publisher_and_content_workflow/chatgpt-oauth-bridge/src/run_openai_sdk_proxy_smoke.py:894: DeprecationWarning: The Assistants API is deprecated in favor of the Responses API   response = client.beta.threads.create_and_run( /Users/sueuncho/Documents/Documents_Codex/03_publisher_and_content_workflow/chatgpt-oauth-bridge/src/r |
| `pass` | `readiness_report` | `0` | `/Library/Developer/CommandLineTools/usr/bin/python3 src/readiness_report.py` | OAuth bridge readiness: complete Complete under the current evidence set.  - met: Documented OpenAI API surface has direct OAuth proof or explicit local/ChatGPT compatibility coverage   official_paths=172; direct_oauth=5; local_bridge=167; api_key_or_admin_key_required=0; incomplete_or_resource_bound=0 - met: Legal local/ChatGPT-backend compatibility routes exist for common app workflows   local_compat_or_chatgpt_backend_bridge=167 - met: Local router compatibility logic passes without network o |
| `pass` | `doctor_strict` | `0` | `/Library/Developer/CommandLineTools/usr/bin/python3 src/doctor_report.py --strict` | OAuth bridge doctor: strict-pass Package health checks pass and the full goal is complete.  state=package_health_ok=True; local_router_ok=True; live_environment_ok=True; full_goal_complete=True coverage=official_paths=172; direct_oauth=5; local_bridge=167; platform_boundary=0 environment=codex_model_discovery_ok=True; localhost_bind_ok=True platform_fallback=enabled=False; mode=boundary; api_key_present=False; access_token_present=False; admin_key_present=False  Next actions: - Use python bridge |

## Next Actions

- Use python bridge.py verdict and reports/goal_audit_latest.md as the launch go/no-go record.
