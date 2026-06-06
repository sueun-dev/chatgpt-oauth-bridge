# OAuth Bridge Readiness

- Generated: `2026-06-06T13:20:39Z`
- Goal complete: `True`
- Hosted OpenAI OAuth complete: `False`
- Local bridge surface complete: `True`
- Bottom line: Complete under the current evidence set.

## Surface Audit

- OpenAPI source: `https://app.stainless.com/api/spec/documented/openai/openapi.documented.yml`
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
| `met` | Current environment can reach Codex model discovery | `ok=True; http_status=200; model_count=5; error=None` |
| `met` | Current environment can bind localhost for HTTP/SDK smoke | `ok=True; host=127.0.0.1; port=49371; error=None` |
| `met` | HTTP proxy smoke has a passing latest report | `proxy_results=108; finished_at=2026-06-06T13:18:50Z` |
| `met` | Official OpenAI Python SDK smoke has a passing latest report | `sdk_results=90; finished_at=2026-06-06T13:20:36Z` |
| `met` | OAuth matrix has a current evidence report | `matrix_results=53; finished_at=2026-06-06T13:12:09Z` |
