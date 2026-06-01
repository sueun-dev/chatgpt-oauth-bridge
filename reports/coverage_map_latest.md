# OpenAI OAuth Bridge Coverage Map

- Generated: `2026-06-01T16:15:21Z`
- Local bridge coverage complete: `True`
- Hosted OpenAI OAuth complete: `False`
- Bottom line: Complete as a local bridge coverage map. This is not a hosted OpenAI Platform OAuth replacement; inspect direct_hosted_oauth_paths versus local_bridge_paths.
- Official paths: `172`
- Source warning: Could not refresh the OpenAPI source in this environment; reused path list from reports/openai_surface_audit_latest.json generated at 2026-06-01T16:11:23Z. Fetch error: RuntimeError: Could not fetch or parse OpenAI OpenAPI paths. https://app.stainless.com/api/spec/documented/openai/openapi.documented.yml: ConnectError: [Errno 8] nodename nor servname provided, or not known; https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml: ConnectError: [Errno 8] nodename nor servname provided, or not known

## Product Groups

| Group | Decision | Direct OAuth | Local Bridge | Blocked/Unproven | Total | Action |
|---|---|---:|---:|---:|---:|---|
| `assistants` | `usable_without_platform_key` | 0 | 2 | 0 | 2 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `audio` | `usable_without_platform_key` | 1 | 5 | 0 | 6 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `batches` | `usable_without_platform_key` | 0 | 3 | 0 | 3 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `chat` | `usable_without_platform_key` | 0 | 3 | 0 | 3 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `chatkit` | `usable_without_platform_key` | 0 | 5 | 0 | 5 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `completions` | `usable_without_platform_key` | 0 | 1 | 0 | 1 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `containers` | `usable_without_platform_key` | 0 | 5 | 0 | 5 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `conversations` | `usable_without_platform_key` | 0 | 4 | 0 | 4 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `embeddings` | `usable_without_platform_key` | 1 | 0 | 0 | 1 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `evals` | `usable_without_platform_key` | 0 | 6 | 0 | 6 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `files` | `usable_without_platform_key` | 0 | 3 | 0 | 3 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `fine_tuning` | `usable_without_platform_key` | 0 | 11 | 0 | 11 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `images` | `usable_without_platform_key` | 0 | 3 | 0 | 3 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `models` | `usable_without_platform_key` | 0 | 2 | 0 | 2 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `moderations` | `usable_without_platform_key` | 0 | 1 | 0 | 1 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `organization/admin` | `usable_without_platform_key` | 0 | 25 | 0 | 25 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `organization/projects` | `usable_without_platform_key` | 0 | 21 | 0 | 21 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `organization/usage` | `usable_without_platform_key` | 0 | 10 | 0 | 10 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `projects` | `usable_without_platform_key` | 0 | 6 | 0 | 6 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `realtime` | `usable_without_platform_key` | 3 | 6 | 0 | 9 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `responses` | `usable_without_platform_key` | 0 | 6 | 0 | 6 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `skills` | `usable_without_platform_key` | 0 | 6 | 0 | 6 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `threads` | `usable_without_platform_key` | 0 | 11 | 0 | 11 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `uploads` | `usable_without_platform_key` | 0 | 4 | 0 | 4 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `vector_stores` | `usable_without_platform_key` | 0 | 10 | 0 | 10 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |
| `videos` | `usable_without_platform_key` | 0 | 8 | 0 | 8 | Can use direct OAuth rows or local bridge rows without Platform credentials; local bridge rows are compatibility substitutes, not hosted OAuth proof. |

## Boundary Examples
