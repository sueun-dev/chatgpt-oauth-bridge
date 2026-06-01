# OAuth Bridge Migration Plan

- Generated: `2026-06-01T16:15:23Z`
- Decision: `ready_to_try_local_bridge`
- Bottom line: Ready to try the local OAuth bridge for the detected OpenAI calls. Run live smoke from a normal shell before treating this as production-ready.
- Inputs: `/v1/embeddings, /v1/assistants, /v1/videos/edits, /v1/fine_tuning/jobs/ftjob_123/cancel`
- Base URL: `http://127.0.0.1:8787/v1`
- Placeholder API key: `oauth-local-proxy`

## Summary

| Metric | Value |
|---|---:|
| Findings | 4 |
| Usable without Platform key | 4 |
| Blocked or unproven | 0 |

## Commands

```bash
python bridge.py serve --host 127.0.0.1 --port 8787
export OPENAI_BASE_URL=http://127.0.0.1:8787/v1 OPENAI_API_KEY=oauth-local-proxy
python bridge.py check /v1/embeddings /v1/assistants /v1/videos/edits /v1/fine_tuning/jobs/ftjob_123/cancel --fail-on-boundary
# optional hybrid Platform fallback:
export OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1 OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=boundary OPENAI_API_KEY=sk-...
# optional exact hosted API preference:
export OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1 OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=prefer OPENAI_API_KEY=sk-...
```

## Steps

- Resolve every blocked_or_unproven finding before claiming an OAuth-only migration.
- Start the bridge in a normal local shell that can bind localhost.
- Point the app SDK/client to OPENAI_BASE_URL and the placeholder OPENAI_API_KEY below.
- For a hybrid migration, use boundary fallback for blocked routes; use prefer mode only when hosted OpenAI API behavior should override local compatibility handlers.
- Run the app's own tests plus bridge.py smoke or bridge.py sdk-smoke from a non-sandboxed shell.
- Add the ci_gate command to prevent Platform-only routes from slipping back in.

## Ready Findings

| Location | Token | Path | Matched Path | Category | Action | Evidence |
|---|---|---|---|---|---|---|
| `<arg>` | `/v1/embeddings` | `/embeddings` | `/embeddings` | `direct_official_oauth_verified` | Can call the official OpenAI path with the tested Codex/ChatGPT OAuth token evidence. Re-run the matrix before relying on it for a different account or date. | `official_api_embeddings_with_oauth=pass` |
| `<arg>` | `/v1/assistants` | `/assistants` | `/assistants` | `local_compat_or_chatgpt_backend_bridge` | Use the local OpenAI-shaped proxy at http://127.0.0.1:8787/v1 or the Python wrapper. This is compatibility, not hosted OpenAI Platform OAuth support. | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass` |
| `<arg>` | `/v1/videos/edits` | `/videos/edits` | `/videos/edits` | `local_compat_or_chatgpt_backend_bridge` | Use the local OpenAI-shaped proxy at http://127.0.0.1:8787/v1 or the Python wrapper. This is compatibility, not hosted OpenAI Platform OAuth support. | `offline:videos_storyboard_sandbox=pass` |
| `<arg>` | `/v1/fine_tuning/jobs/ftjob_123/cancel` | `/fine_tuning/jobs/ftjob_123/cancel` | `/fine_tuning/jobs/{fine_tuning_job_id}/cancel` | `local_compat_or_chatgpt_backend_bridge` | Use the local OpenAI-shaped proxy at http://127.0.0.1:8787/v1 or the Python wrapper. This is compatibility, not hosted OpenAI Platform OAuth support. | `offline:fine_tuning_jobs=pass` |

## Blocked Or Unproven Findings

- None

## Other Findings

- None
