# OAuth Bridge Status

- Generated: `2026-06-01T17:49:54Z`
- Goal complete: `False`
- Bottom line: Not complete: every documented path is mapped to direct OAuth or explicit local compatibility, but only 5 paths are direct hosted OAuth and this environment cannot prove live Codex network access and localhost SDK smoke.
- Base URL: `http://127.0.0.1:8787/v1`
- Placeholder API key: `oauth-local-proxy`

## Coverage

| Category | Paths |
|---|---:|
| `direct_official_oauth_verified` | 5 |
| `local_compat_or_chatgpt_backend_bridge` | 167 |

## Current Environment

| Check | Value |
|---|---|
| Codex model discovery | `False` |
| Codex model discovery error | `ConnectError` |
| Localhost bind | `False` |
| Localhost bind error | `PermissionError` |
| DNS/network blocked | `True` |
| Localhost socket denied | `True` |
| Environment report time | `2026-06-01T17:48:37Z` |

## Platform Fallback

| Check | Value |
|---|---|
| Enabled | `False` |
| Mode | `boundary` |
| API key present | `False` |
| Access token present | `False` |
| Admin key present | `False` |

## Smoke Evidence

| Report | Results | All Pass | Finished |
|---|---:|---|---|
| `offline` | 36 | `True` | `2026-06-01T17:48:38Z` |
| `http_proxy` | 74 | `True` | `2026-05-29T23:37:40Z` |
| `openai_python_sdk` | 65 | `True` | `2026-05-29T23:39:02Z` |
| `oauth_matrix` | 53 | `None` | `2026-05-29T21:55:56Z` |

## Commands

- `start_proxy`: `python bridge.py serve --host 127.0.0.1 --port 8787`
- `quickstart`: `python bridge.py quickstart`
- `live_check`: `python bridge.py live-check`
- `publish_check`: `python bridge.py publish-check`
- `publish_api`: `python bridge.py publish-api --dry-run`
- `publish_gate`: `bash reports/openai_bridge_publish_gate.sh --push`
- `finish_gate`: `bash reports/openai_bridge_finish_gate.sh --push`
- `status`: `python bridge.py status`
- `verdict`: `python bridge.py verdict`
- `strict_verdict`: `python bridge.py verdict --strict`
- `doctor`: `python bridge.py doctor`
- `readiness`: `python bridge.py readiness`
- `guide`: `python bridge.py guide`
- `coverage`: `python bridge.py coverage`
- `fallback`: `python bridge.py fallback`
- `enable_boundary_fallback`: `export OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1 OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=boundary OPENAI_API_KEY=sk-...`
- `enable_prefer_platform`: `export OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1 OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=prefer OPENAI_API_KEY=sk-...`
- `check_app`: `python bridge.py check path/to/your/app --fail-on-boundary`
- `migration_plan`: `python bridge.py migrate path/to/your/app --fail-on-boundary`

## Next Actions

- Run live HTTP/SDK smoke from a shell that can bind localhost.
- Run from an environment with network access before relying on live model-backed calls.
- Use python bridge.py quickstart for the first-run bundle: env, CI gate, route policy, and full-goal verdict.
- Use python bridge.py live-check from a normal local shell for the launch gate: environment, HTTP proxy smoke, SDK smoke, readiness, and strict doctor.
- Use python bridge.py migrate path/to/your/app --fail-on-boundary for a paste-ready migration plan.
- Use python bridge.py verdict for the full-goal completion audit and user-facing go/no-go answer.
- Use python bridge.py coverage for product-group coverage and boundary decisions.
- Use python bridge.py policy for a machine-readable allow/deny/fallback route policy.
- Use python bridge.py boundaries for a safe playbook covering every remaining Platform/Admin boundary.
- Use python bridge.py fallback to inspect optional Platform/Admin credential forwarding state.
- Use python bridge.py check path/to/your/app --fail-on-boundary before migrating an app.
- Use python bridge.py config for SDK/curl/env snippets.
- Use python bridge.py serve --port 8787 in a normal local shell when localhost binding is allowed.

## Git

- Branch: `## main...origin/main [ahead 1]`
- Changed files: `0`
