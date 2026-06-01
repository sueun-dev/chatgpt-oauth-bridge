# OAuth Bridge Readiness

- Generated: `2026-06-01T17:49:54Z`
- Goal complete: `False`
- Hosted OpenAI OAuth complete: `False`
- Local bridge surface complete: `True`
- Bottom line: Not complete: every documented path is mapped to direct OAuth or explicit local compatibility, but only 5 paths are direct hosted OAuth and this environment cannot prove live Codex network access and localhost SDK smoke.

## Surface Audit

- OpenAPI source: `existing-report:https://app.stainless.com/api/spec/documented/openai/openapi.documented.yml`
- Official paths: `172`

| Category | Count |
|---|---:|
| `direct_official_oauth_verified` | 5 |
| `local_compat_or_chatgpt_backend_bridge` | 167 |

## Requirements

| Status | Requirement | Evidence |
|---|---|---|
| `met` | Documented OpenAI API surface has direct OAuth proof or explicit local/ChatGPT compatibility coverage | `official_paths=172; direct_oauth=5; local_bridge=167; api_key_or_admin_key_required=0; incomplete_or_resource_bound=0` |
| `met` | Legal local/ChatGPT-backend compatibility routes exist for common app workflows | `local_compat_or_chatgpt_backend_bridge=167` |
| `met` | Local router compatibility logic passes without network or localhost sockets | `offline_results=36; report=reports/router_offline_smoke_latest.json` |
| `not_met` | Current environment can reach Codex model discovery | `ok=False; http_status=None; model_count=None; error=[Errno 8] nodename nor servname provided, or not known` |
| `not_met` | Current environment can bind localhost for HTTP/SDK smoke | `ok=False; host=127.0.0.1; port=0; error=[Errno 1] Operation not permitted` |
| `met` | HTTP proxy smoke has a passing latest report | `proxy_results=74; finished_at=2026-05-29T23:37:40Z` |
| `met` | Official OpenAI Python SDK smoke has a passing latest report | `sdk_results=65; finished_at=2026-05-29T23:39:02Z` |
| `met` | OAuth matrix has a current evidence report | `matrix_results=53; finished_at=2026-05-29T21:55:56Z` |

## Blockers

- Current environment cannot reach Codex model discovery.
- Current environment cannot bind localhost for HTTP/SDK smoke.

## Current Environment Warnings

- Current environment cannot reach Codex model discovery.
- Current environment cannot bind localhost for HTTP/SDK smoke.
