# OpenAI Usage Compatibility Check

- Generated: `2026-06-01T16:15:23Z`
- Inputs: `/v1/embeddings, /v1/assistants, /v1/videos/edits, /v1/fine_tuning/jobs/ftjob_123/cancel`
- Findings: `4`
- Usable without Platform key: `4`
- Blocked or unproven: `0`

## Category Counts

| Category | Count |
|---|---:|
| `direct_official_oauth_verified` | 1 |
| `local_compat_or_chatgpt_backend_bridge` | 3 |

## Findings

| Source | Line | Token | Path | Matched Path | Category | Decision | Evidence |
|---|---:|---|---|---|---|---|---|
| `<arg>` |  | `/v1/embeddings` | `/embeddings` | `/embeddings` | `direct_official_oauth_verified` | Official OAuth verified | `official_api_embeddings_with_oauth=pass` |
| `<arg>` |  | `/v1/assistants` | `/assistants` | `/assistants` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass` |
| `<arg>` |  | `/v1/videos/edits` | `/videos/edits` | `/videos/edits` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:videos_storyboard_sandbox=pass` |
| `<arg>` |  | `/v1/fine_tuning/jobs/ftjob_123/cancel` | `/fine_tuning/jobs/ftjob_123/cancel` | `/fine_tuning/jobs/{fine_tuning_job_id}/cancel` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:fine_tuning_jobs=pass` |
