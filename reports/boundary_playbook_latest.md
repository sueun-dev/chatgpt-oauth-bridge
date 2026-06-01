# OAuth Boundary Playbook

- Generated: `2026-06-01T16:15:22Z`
- Boundary map complete: `True`
- Hosted OpenAI OAuth complete: `False`
- Bottom line: No blocked path remains in the local bridge map, but hosted OpenAI OAuth is directly verified for 5 paths; 167 paths are local or ChatGPT-backend compatibility.
- Official paths: `172`
- Ready paths: `172`
- Direct hosted OAuth paths: `5`
- Local bridge paths: `167`
- Blocked or unproven paths: `0`
- Source warning: Could not refresh the OpenAPI source in this environment; reused path list from reports/openai_surface_audit_latest.json generated at 2026-06-01T16:11:23Z. Fetch error: RuntimeError: Could not fetch or parse OpenAI OpenAPI paths. https://app.stainless.com/api/spec/documented/openai/openapi.documented.yml: ConnectError: [Errno 8] nodename nor servname provided, or not known; https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml: ConnectError: [Errno 8] nodename nor servname provided, or not known

## Safe Modes

- OAuth-only mode: run the strict gate and disable every blocked route.
- Hybrid mode: enable Platform fallback explicitly and provide the right official credential for each boundary route.
- Admin mode: keep org/project/admin paths behind a separate Admin credential and explicit app feature flag.

## Commands

```bash
python bridge.py check path/to/your/app --fail-on-boundary
python bridge.py migrate path/to/your/app --fail-on-boundary
python bridge.py status
python bridge.py coverage
export OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1
export OPENAI_API_KEY=sk-...
export OPENAI_ACCESS_TOKEN=official-workload-identity-bearer
export OPENAI_ADMIN_KEY=sk-admin-or-ek-...
```

## Groups

| Group | Mode | Direct OAuth | Local Bridge | Blocked/Unproven | Credential Envs | Action |
|---|---|---:|---:|---:|---|---|
| `assistants` | `oauth_or_local_only` | 0 | 2 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `audio` | `oauth_or_local_only` | 1 | 5 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `batches` | `oauth_or_local_only` | 0 | 3 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `chat` | `oauth_or_local_only` | 0 | 3 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `chatkit` | `oauth_or_local_only` | 0 | 5 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `completions` | `oauth_or_local_only` | 0 | 1 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `containers` | `oauth_or_local_only` | 0 | 5 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `conversations` | `oauth_or_local_only` | 0 | 4 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `embeddings` | `oauth_or_local_only` | 1 | 0 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `evals` | `oauth_or_local_only` | 0 | 6 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `files` | `oauth_or_local_only` | 0 | 3 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `fine_tuning` | `oauth_or_local_only` | 0 | 11 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `images` | `oauth_or_local_only` | 0 | 3 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `models` | `oauth_or_local_only` | 0 | 2 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `moderations` | `oauth_or_local_only` | 0 | 1 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `organization/admin` | `oauth_or_local_only` | 0 | 25 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `organization/projects` | `oauth_or_local_only` | 0 | 21 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `organization/usage` | `oauth_or_local_only` | 0 | 10 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `projects` | `oauth_or_local_only` | 0 | 6 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `realtime` | `oauth_or_local_only` | 3 | 6 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `responses` | `oauth_or_local_only` | 0 | 6 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `skills` | `oauth_or_local_only` | 0 | 6 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `threads` | `oauth_or_local_only` | 0 | 11 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `uploads` | `oauth_or_local_only` | 0 | 4 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `vector_stores` | `oauth_or_local_only` | 0 | 10 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |
| `videos` | `oauth_or_local_only` | 0 | 8 | 0 | `` | Use direct hosted OAuth only for direct rows; route local rows through the local bridge. Local rows are substitutes, not hosted Platform OAuth proof. |

## Blocked Or Unproven Paths


## Warnings

- Platform fallback is hybrid routing, not ChatGPT/Codex OAuth support.
- OPENAI_ACCESS_TOKEN is for official OpenAI workload-identity-style bearer tokens, not the local ChatGPT/Codex OAuth token.
- Admin/project/org paths should use a separate Admin credential and should not be enabled by accident in user apps.
- Resource-bound Realtime paths still need live call IDs before they can be marked complete.
