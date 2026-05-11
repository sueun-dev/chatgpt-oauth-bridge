# Expanded OAuth Sweep

Last run: `2026-05-11T22:55:58Z` to `2026-05-11T22:58:14Z`

Runner:

```bash
python src/run_oauth_matrix.py
python src/run_deep_oauth_research.py
```

## Status Counts

- `pass`: 13
- `auth_accepted_request_invalid`: 2
- `expected_blocked`: 30
- `fail`: 0

## Passed

- Hermes/Codex OAuth token inventory
- No Platform API-key environment variables present
- Codex model discovery
- Codex text response
- Codex vision input
- Codex image generation
- Codex drawing generation
- Official audio transcription: `POST /v1/audio/transcriptions`
- Official Realtime client secret: `POST /v1/realtime/client_secrets`
- Official Realtime WebSocket audio using the OAuth-created ephemeral key
- Official Realtime transcription client secret:
  `POST /v1/realtime/client_secrets` with `session.type="transcription"`
- Official Realtime calls:
  `POST /v1/realtime/calls` with multipart SDP returned `201`
- Official embeddings: `POST /v1/embeddings`

## Realtime Calls

- `POST /v1/realtime/calls`

The first broad sweep sent JSON and got the expected `application/sdp` shape
error. The deep sweep then sent both `application/sdp` and Codex-style multipart
requests. The fake SDP returned `invalid_offer`; the later realistic multipart
WebRTC offer returned `201`, a `Location` header, and an answer SDP. That route
is now confirmed usable with OAuth when the payload is a real SDP offer shape.

## Deep ChatGPT/Codex Backend Findings

Last deep run: `2026-05-11T22:47:10Z` to `2026-05-11T22:47:32Z`

Passed:

- `GET /backend-api/wham/usage`
- `GET /backend-api/codex/models` with `7` returned models
- `POST /backend-api/codex/responses` with streaming text
- `GET /backend-api/wham/tasks/list` with `0` returned tasks
- `GET /backend-api/wham/tasks/{task_id}` route shape; dummy ID returned
  `Invalid task ID`
- `GET /backend-api/wham/tasks/{task_id}/turns/{turn_id}/sibling_turns` route
  shape; dummy ID returned `Invalid task ID`
- `GET /backend-api/wham/environments` with `5` returned environments
- `GET /backend-api/wham/environments/by-repo/github/openai/codex`
- `POST /backend-api/files`
- signed upload URL `PUT`
- `POST /backend-api/files/{file_id}/uploaded`
- signed download URL probe `GET`
- `GET /backend-api/plugins/list` with `121` returned items
- `GET /backend-api/plugins/featured?platform=codex` with `20` returned items
- `GET /backend-api/plugins/featured?platform=chat` with `19` returned items
- `GET /backend-api/plugins/export/curated` with a `files.openai.com` bundle
  pointer
- `GET /backend-api/connectors/directory/list` with `892` returned apps
- `GET /backend-api/connectors/directory/list_workspace` with `892` returned
  apps
- `GET /backend-api/wham/agent-identities/jwks`
- `GET /backend-api/me`, summarized only
- `GET /backend-api/accounts/check/v4-2023-04-27`, summarized only
- `GET /backend-api/aura/site_status` for Browser Use policy status
- `POST /backend-api/codex/responses/compact`
- `POST /backend-api/wham/apps` initialize
- `POST /backend-api/wham/apps` `tools/list` with `111` returned tools
- `POST /backend-api/wham/apps` `resources/list`
- `POST /backend-api/wham/apps` `prompts/list`
- `POST /backend-api/wham/apps` `tools/call` for a safe public GitHub
  repository search
- `POST /v1/realtime/calls` Codex-style multipart SDP with `201` and answer SDP

Source-backed but not auto-run because they mutate account/workspace state:

- `POST /backend-api/wham/tasks`
- `POST /backend-api/wham/remote/control/server/enroll`
- `WSS /backend-api/wham/remote/control/server`
- `POST /backend-api/public/plugins/workspace/upload-url`
- `POST /backend-api/public/plugins/workspace`
- `POST /backend-api/public/plugins/workspace/{remote_plugin_id}`
- `PUT /backend-api/ps/plugins/{remote_plugin_id}/shares`
- `DELETE /backend-api/public/plugins/workspace/{remote_plugin_id}`
- `POST /backend-api/ps/plugins/{plugin_id}/install`
- `POST /backend-api/plugins/{plugin_id}/uninstall`
- `POST /backend-api/wham/accounts/send_add_credits_nudge_email`
- `POST /api/codex/accounts/send_add_credits_nudge_email`
- `POST /backend-api/codex/analytics-events/events`

Source-backed but not OAuth:

- `codex-responses-api-proxy` forwards `/v1/responses`, but it reads
  `OPENAI_API_KEY` from stdin, so it is not an OAuth-only path.

Still rejected or unavailable:

- `https://chatgpt.com/api/codex/usage`, `/models`, `/tasks/list`,
  `/environments`, and `/config/requirements`: HTML `404` here.
- `https://chatgpt.com/api/codex/apps` and `/responses`: `302` redirect here.
- `GET /backend-api/ps/plugins/list`, `/ps/plugins/installed`, and
  `/ps/plugins/workspace/shared`: 404 here,
  even though the current openai/codex source has code paths for them.
- `GET /backend-api/ps/plugins/workspace/created`: 404 here.
- `GET /backend-api/accounts/<account-id>/settings`: 401
  `Must use workspace account for this operation`.
- `POST /backend-api/codex/memories/trace_summarize`: 404.
- `POST /backend-api/codex/realtime/calls`: 404. The official
  `api.openai.com/v1/realtime/calls` route is the working one for call setup.

## Blocked

The following returned OAuth/API-key/Admin-key boundary errors or route-level
rejections:

- Models
- Files
- Chat Completions
- Legacy Completions
- Responses
- Responses with web search
- Image generations
- Image edits
- Image variations
- TTS
- Audio translations
- Moderations
- Vector stores
- Batches
- Fine-tuning jobs
- Evals
- Containers
- Videos list/create
- Upload create/cancel
- Assistants list
- Thread create/delete
- ChatKit session creation
- Organization projects
- Organization users
- Organization admin keys
- Audit logs
- Usage completions
- Costs

## Source Boundary

Official docs checked during the build:

- `https://platform.openai.com/docs/api-reference/authentication`
- `https://platform.openai.com/docs/guides/realtime-websocket`
- `https://platform.openai.com/docs/guides/realtime-transcription`
- `https://platform.openai.com/docs/api-reference/realtime-sessions`
- `https://platform.openai.com/docs/api-reference/images/overview`
- `https://platform.openai.com/docs/guides/video-generation`
- `https://platform.openai.com/docs/api-reference/uploads/create`
- `https://platform.openai.com/docs/api-reference/containers`
- `https://platform.openai.com/docs/api-reference/evals`
- `https://platform.openai.com/docs/guides/chatkit`
- `https://platform.openai.com/docs/api-reference/projects`
- `https://platform.openai.com/docs/api-reference/usage/completions_object`

The docs say the public Platform API uses API keys. The OAuth behavior in this
project is therefore empirical for the local ChatGPT/Codex OAuth token, not a
public OpenAI guarantee.
