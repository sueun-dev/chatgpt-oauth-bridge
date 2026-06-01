# Official Boundary

This file keeps the boundary explicit so the test output is not misleading.

## Public OpenAI API

The OpenAI API reference documents HTTP bearer authentication for the REST,
streaming, and realtime APIs. The documented bearer credentials are Platform
API keys or short-lived access tokens created with OpenAI workload identity
federation. They are not the same thing as a local ChatGPT/Codex OAuth token:

- `https://platform.openai.com/docs/api-reference/authentication`
- `https://developers.openai.com/api/docs/guides/workload-identity-federation`
- `https://platform.openai.com/docs/quickstart`
- `https://platform.openai.com/docs/guides/realtime-websocket`
- `https://platform.openai.com/docs/api-reference/realtime-sessions`

That means the normal Platform endpoints such as these are not expected to work
with a ChatGPT/Codex OAuth token unless this repo has direct current evidence
for that route:

- `https://api.openai.com/v1/responses`
- `https://api.openai.com/v1/images/generations`
- `https://api.openai.com/v1/audio/speech`
- `https://api.openai.com/v1/audio/transcriptions`
- `https://api.openai.com/v1/realtime/...`
- `https://api.openai.com/v1/embeddings`
- `https://api.openai.com/v1/conversations`
- `https://api.openai.com/v1/skills`
- `https://api.openai.com/v1/moderations`
- `https://api.openai.com/v1/files`
- `https://api.openai.com/v1/vector_stores`
- `https://api.openai.com/v1/uploads`
- `https://api.openai.com/v1/batches`
- `https://api.openai.com/v1/fine_tuning/jobs`
- `https://api.openai.com/v1/evals`
- `https://api.openai.com/v1/containers`
- `https://api.openai.com/v1/videos`
- `https://api.openai.com/v1/assistants`
- `https://api.openai.com/v1/threads`
- `https://api.openai.com/v1/chatkit/sessions`

The local sweep found exceptions in this account for:

- `POST /v1/audio/transcriptions`
- `POST /v1/realtime/client_secrets`
- Realtime WebSocket with the OAuth-created ephemeral key
- Realtime transcription setup through `POST /v1/realtime/client_secrets` with
  `session.type="transcription"`. The local proxy exposes
  `/v1/realtime/transcription_sessions` as a compatibility alias over that
  OAuth-accepted client-secret route.
- Realtime translation setup through
  `POST /v1/realtime/translations/client_secrets`.
- `POST /v1/embeddings`
- `POST /v1/realtime/calls`; OAuth reached the route with both documented
  `application/sdp` and multipart shapes. The realistic multipart WebRTC offer
  returned `201`, a `Location` header, and an answer SDP.
  The lifecycle routes under `/v1/realtime/calls/{call_id}/...` are exposed by
  the local proxy as state-recording compatibility handlers, not as hosted
  lifecycle mutation proof.
- `POST /v1/conversations` reached route validation, but the current probe
  stopped at `Project ID must be set for the request`; it is not proven as a
  complete OAuth replacement.
- `POST /v1/realtime/sessions` returned invalid-url/not-routed in this
  deployment, so the local proxy exposes it only as a compatibility alias over
  `/v1/realtime/client_secrets`.

The current `reports/openai_surface_audit_latest.md` classifies `172`
documented OpenAI API paths: `5` direct official OAuth-verified paths, `167`
local/ChatGPT-backend compatibility paths, `0` API-key/Admin-key required
paths, `0` not available in this deployment, `0` auth-reached-but-not-complete
paths, and `0` resource-bound paths.

On the current verification pass, the official OpenAI Developer Docs endpoint
index also returned `172` paths under `https://api.openai.com/v1`, matching the
local audit count. That docs check is endpoint parity evidence only: the local
shell still cannot refresh the OpenAPI source directly in this restricted
environment. The same official spec shows `/v1/videos` examples using
`OPENAI_API_KEY`, while `/v1/organization/projects` uses `AdminApiKeyAuth` and
`OPENAI_ADMIN_KEY`.

The local compatibility count includes `/v1/organization...` and
`/v1/projects...` as a local Organization/Project/Usage sandbox for SDK/app
workflows. It does not read real organization usage/costs, expose real users or
keys, or mutate hosted Admin resources; those still require official
Platform/Admin credentials.

The local compatibility count includes `/v1/fine_tuning/jobs...` and
`/v1/fine_tuning/checkpoints/.../permissions...` as local job lifecycle,
event, checkpoint, and permission metadata stores for SDK/app workflows. It
does not start hosted OpenAI fine-tuning, produce a hosted fine-tuned model, or
change real organization checkpoint permissions.

The local compatibility count includes `/v1/videos...` as local video
storyboard/job metadata and JSON content-manifest routes for SDK/app workflows.
It does not render hosted Sora video, create OpenAI-hosted MP4 bytes, or
retrieve real hosted video content; those still require official Platform
credentials and eligible hosted video access.

The local compatibility count includes `POST /v1/fine_tuning/alpha/graders/run`
and `POST /v1/fine_tuning/alpha/graders/validate` for local `string_check` and
`multi` grader preflight.

The local compatibility count also includes `POST /v1/realtime/sessions` and
`POST /v1/realtime/transcription_sessions` as aliases over the OAuth-accepted
Realtime client-secret endpoint. That is not direct proof that the older hosted
session routes accept the ChatGPT/Codex OAuth token.

The local compatibility count also includes
`POST /v1/realtime/calls/{call_id}/accept`,
`POST /v1/realtime/calls/{call_id}/hangup`,
`POST /v1/realtime/calls/{call_id}/refer`, and
`POST /v1/realtime/calls/{call_id}/reject` as local state transitions. They are
for SDK/app lifecycle compatibility after call setup; they do not prove hosted
OpenAI will mutate an arbitrary call id with this OAuth token.

The local compatibility count also includes `/v1/audio/voices` and
`/v1/audio/voice_consents...` as local metadata stores. Official custom voice
creation and consent uploads are still Platform features for eligible accounts;
the local proxy only lets SDK/apps exercise voice IDs, consent metadata, and
custom-voice workflow shapes.

The Realtime WebRTC docs describe `/v1/realtime/calls` as an SDP/WebRTC route,
not a JSON endpoint:

- `https://platform.openai.com/docs/guides/realtime-webrtc`
- `https://platform.openai.com/docs/api-reference/realtime`

## ChatGPT/GPT Actions OAuth

OpenAI also documents OAuth for GPT Actions, but that OAuth is for ChatGPT
signing a user into an external service's API. It is not an OAuth replacement
for OpenAI Platform API keys:

- `https://platform.openai.com/docs/actions/authentication`

## MCP OAuth

OpenAI Responses can pass OAuth access tokens to remote MCP servers through a
tool configuration. That OAuth token belongs to the third-party MCP server, not
to the OpenAI API itself:

- `https://platform.openai.com/docs/guides/tools-remote-mcp`

## Hermes Codex OAuth

Hermes has a separate `openai-codex` provider. It uses OpenAI/Codex OAuth and
then calls:

```text
https://chatgpt.com/backend-api/codex
```

Additional ChatGPT/Codex backend routes confirmed locally with the same OAuth
token:

- `https://chatgpt.com/backend-api/files`
- `https://chatgpt.com/backend-api/files/{file_id}/uploaded`
- `https://chatgpt.com/backend-api/plugins/list`
- `https://chatgpt.com/backend-api/plugins/featured`
- `https://chatgpt.com/backend-api/plugins/export/curated`
- `https://chatgpt.com/backend-api/connectors/directory/list`
- `https://chatgpt.com/backend-api/connectors/directory/list_workspace`
- `https://chatgpt.com/backend-api/wham/tasks/list`
- `https://chatgpt.com/backend-api/wham/tasks/{task_id}`
- `https://chatgpt.com/backend-api/wham/tasks/{task_id}/turns/{turn_id}/sibling_turns`
- `https://chatgpt.com/backend-api/wham/environments`
- `https://chatgpt.com/backend-api/wham/environments/by-repo/...`
- `https://chatgpt.com/backend-api/wham/apps`
- `https://chatgpt.com/backend-api/wham/usage`
- `https://chatgpt.com/backend-api/wham/agent-identities/jwks`
- `https://chatgpt.com/backend-api/me`
- `https://chatgpt.com/backend-api/accounts/check/v4-2023-04-27`
- `https://chatgpt.com/backend-api/aura/site_status`
- `https://chatgpt.com/backend-api/codex/models`
- `https://chatgpt.com/backend-api/codex/responses`
- `https://chatgpt.com/backend-api/codex/responses/compact`

The official `openai/codex` source also contains these OAuth routes, but they
are not run by the default probe because they mutate state:

- `https://chatgpt.com/backend-api/wham/tasks`
- `https://chatgpt.com/backend-api/wham/remote/control/server/enroll`
- `wss://chatgpt.com/backend-api/wham/remote/control/server`
- `https://chatgpt.com/backend-api/public/plugins/workspace/upload-url`
- `https://chatgpt.com/backend-api/public/plugins/workspace`
- `https://chatgpt.com/backend-api/public/plugins/workspace/{remote_plugin_id}`
- `https://chatgpt.com/backend-api/ps/plugins/{remote_plugin_id}/shares`
- `https://chatgpt.com/backend-api/ps/plugins/{plugin_id}/install`
- `https://chatgpt.com/backend-api/plugins/{plugin_id}/uninstall`
- `https://chatgpt.com/backend-api/wham/accounts/send_add_credits_nudge_email`
- `https://chatgpt.com/api/codex/accounts/send_add_credits_nudge_email`

The official `openai/codex` repo also contains `https://chatgpt.com/api/codex`
style paths. Those were probed directly; in this current deployment they did
not work from this OAuth token, while the `backend-api/wham` equivalents did.
The newer `backend-api/ps/plugins/...` workspace plugin service paths in the
source also returned `404` here; the older plugin catalog/export routes worked.

Local source references:

- `<hermes-install>/hermes_cli/auth.py`
- `<hermes-install>/agent/auxiliary_client.py`
- `<hermes-install>/plugins/image_gen/openai-codex/__init__.py`
- official source clone used for route research:
  `/tmp/openai-codex-oauth-research-latest` at
  `4859d80ffeec76cc59c95fd274157c6b5560b4d2`

## Admin API Boundary

OpenAI documents organization/project/admin endpoints as Admin API key
endpoints:

- `https://platform.openai.com/docs/api-reference/projects`
- `https://platform.openai.com/docs/api-reference/audit-logs`
- `https://platform.openai.com/docs/api-reference/admin-api-keys/listget`
- `https://platform.openai.com/docs/api-reference/usage/completions_object`

The local OAuth sweep tried list/read-only probes for those surfaces and they
returned `401`.
The local proxy therefore exposes a sandbox-shaped substitute for app
development, while keeping real hosted Admin data and mutations behind official
Admin credentials.
