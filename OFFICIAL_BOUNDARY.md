# Official Boundary

This file keeps the boundary explicit so the test output is not misleading.

## Public OpenAI API

The OpenAI API reference documents API-key authentication for the REST,
streaming, and realtime APIs:

- `https://platform.openai.com/docs/api-reference/authentication`
- `https://platform.openai.com/docs/quickstart`
- `https://platform.openai.com/docs/guides/realtime-websocket`
- `https://platform.openai.com/docs/api-reference/realtime-sessions`

That means the normal Platform endpoints such as these are not expected to work
with a ChatGPT/Codex OAuth token:

- `https://api.openai.com/v1/responses`
- `https://api.openai.com/v1/images/generations`
- `https://api.openai.com/v1/audio/speech`
- `https://api.openai.com/v1/audio/transcriptions`
- `https://api.openai.com/v1/realtime/...`
- `https://api.openai.com/v1/embeddings`
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
  `session.type="transcription"`. The older
  `/v1/realtime/transcription_sessions` shape now returns
  `400 Unknown beta requested: 'realtime'` here.
- `POST /v1/embeddings`
- `POST /v1/realtime/calls`; OAuth reached the route with both documented
  `application/sdp` and multipart shapes. The realistic multipart WebRTC offer
  returned `201`, a `Location` header, and an answer SDP.

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
