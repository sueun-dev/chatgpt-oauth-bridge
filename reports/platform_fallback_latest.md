# Platform Fallback Status

- Generated: `2026-06-06T12:44:14Z`
- Enabled: `False`
- Mode: `boundary`
- Base URL: `https://api.openai.com/v1`
- API key present: `False`
- Access token present: `False`
- Admin key present: `False`

## Setup

```bash
export OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1
export OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=boundary
# or, for exact hosted API behavior before local compatibility:
export OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=prefer
export OPENAI_API_KEY=sk-...
export OPENAI_ACCESS_TOKEN=official-workload-identity-bearer
export OPENAI_ADMIN_KEY=sk-admin-or-ek-...
export OAUTH_BRIDGE_PLATFORM_BASE_URL=https://api.openai.com/v1
```

## Path Checks

| Path | Matched Path | Category | Mode | Credential Env | Accepted Envs | Present | Can Forward |
|---|---|---|---|---|---|---|---|
| `/v1/videos/edits` | `/videos/edits` | `local_compat_or_chatgpt_backend_bridge` | `boundary` | `OPENAI_API_KEY` | `OPENAI_API_KEY, OPENAI_ACCESS_TOKEN` | `False` | `False` |
| `/v1/fine_tuning/jobs/ftjob_123/cancel` | `/fine_tuning/jobs/{fine_tuning_job_id}/cancel` | `local_compat_or_chatgpt_backend_bridge` | `boundary` | `OPENAI_API_KEY` | `OPENAI_API_KEY, OPENAI_ACCESS_TOKEN` | `False` | `False` |
| `/v1/organization/projects` | `/organization/projects` | `local_compat_or_chatgpt_backend_bridge` | `boundary` | `OPENAI_ADMIN_KEY` | `OPENAI_ADMIN_KEY` | `False` | `False` |

## Warnings

- This is not ChatGPT/Codex OAuth. It is an explicit Platform/Admin credential fallback.
- OPENAI_ACCESS_TOKEN is for official OpenAI workload identity federation style bearer tokens, not a ChatGPT/Codex OAuth session token.
- The local SDK placeholder value oauth-local-proxy is ignored as a Platform credential.
- The local proxy never prints or stores the key value in reports.
- Keep Admin credentials separate; organization and project administration paths require the admin-key environment.
