# OAuth Results Summary

Last full run:

- Time: `2026-05-11T22:55:58Z` to `2026-05-11T22:58:14Z`
- Runtime auth source: `~/.codex/auth.json` Codex CLI OAuth token
- Hermes `~/.hermes/auth.json` was present but expired; its refresh returned
  `401`, so the runner fell back to the live Codex CLI OAuth token.
- No `OPENAI_API_KEY` or `OPENAI_ADMIN_KEY` was present in the test process.
- Full report: `reports/latest.md`
- Scope: `45` OAuth-only probes across Codex, text, vision, image, audio,
  Realtime, embeddings, legacy completions, Responses tools, files/uploads,
  vector stores, batches, fine-tuning, evals, containers, videos, Assistants,
  ChatKit, and Admin/Usage APIs.

Status counts:

- `pass`: 13
- `auth_accepted_request_invalid`: 2
- `expected_blocked`: 30

Last deep backend run:

- Time: `2026-05-11T22:47:10Z` to `2026-05-11T22:47:32Z`
- Full report: `reports/deep_oauth_research_latest.md`
- Apps MCP tool inventory: `reports/codex_apps_tools_latest.md`
- `openai/codex` source HEAD checked: `4859d80ffeec76cc59c95fd274157c6b5560b4d2`
- Scope: focused ChatGPT/Codex backend routes from the official `openai/codex`
  repo plus the Realtime WebRTC call shape and source-backed side-effect
  routes.

Deep status counts:

- `pass`: 24
- `auth_accepted_request_invalid`: 25
- `expected_blocked`: 1
- `not_run_side_effect`: 6
- `not_run_no_candidate`: 2
- `not_oauth_api_key_proxy`: 1

## OAuth Surfaces That Worked

Codex/ChatGPT OAuth backend:

- Model discovery through `https://chatgpt.com/backend-api/codex`
- Text response with `gpt-5.4-mini`
- Vision input with `gpt-5.4-mini`
- Image generation through the Codex Responses `image_generation` tool
- Drawing generation through the same image tool
- Remote compaction through `POST /backend-api/codex/responses/compact`
- ChatGPT backend file upload/finalize/download through
  `POST /backend-api/files` and `POST /backend-api/files/{file_id}/uploaded`
- ChatGPT plugin catalog reads through `GET /backend-api/plugins/list`
  (`121` items), `GET /backend-api/plugins/featured?platform=codex`
  (`20` items), and `platform=chat` (`19` items)
- ChatGPT connector directory reads through
  `GET /backend-api/connectors/directory/list` and
  `GET /backend-api/connectors/directory/list_workspace` (`892` apps each in
  this account snapshot)
- ChatGPT Codex task/environment reads through `GET /backend-api/wham/tasks/list`
  (`0` current tasks) and `GET /backend-api/wham/environments` (`5`
  environments)
- ChatGPT Codex task detail and sibling-turn route shapes through
  `GET /backend-api/wham/tasks/{task_id}` and
  `GET /backend-api/wham/tasks/{task_id}/turns/{turn_id}/sibling_turns`.
  Dummy IDs returned `Invalid task ID`, which confirms route/auth shape without
  reading a real task.
- ChatGPT Codex repo-environment lookup through
  `GET /backend-api/wham/environments/by-repo/github/openai/codex` (`0`
  matching environments, route worked)
- ChatGPT identity/account shape reads through `GET /backend-api/me` and
  `GET /backend-api/accounts/check/v4-2023-04-27`; sensitive values are
  redacted in reports
- Browser Use/Aura site policy status through
  `GET /backend-api/aura/site_status?site_url=https://example.com/&url_request_source=codex_browser_use`
- Codex Apps MCP endpoint through `POST /backend-api/wham/apps`:
  initialize passed, `tools/list` returned `111` tools, `resources/list` and
  `prompts/list` returned empty lists. One safe public GitHub repository search
  through `tools/call` also worked.
- ChatGPT/Codex usage through `GET /backend-api/wham/usage`

OpenAI API endpoints that accepted the Codex OAuth token in this account:

- `POST /v1/audio/transcriptions`
- `POST /v1/realtime/client_secrets`
- Realtime WebSocket using the OAuth-created ephemeral key
- Realtime transcription client secret via `POST /v1/realtime/client_secrets`
  with `session.type="transcription"`. The older
  `/v1/realtime/transcription_sessions` shape now returns `400 Unknown beta
  requested: 'realtime'`.
- `POST /v1/embeddings`
- `POST /v1/realtime/calls` accepted OAuth with both `application/sdp` and
  Codex-style multipart request shapes. With a realistic WebRTC offer, the
  Codex-style multipart request returned `201`, a `Location` header, and an
  answer SDP.

Source-backed but not auto-run because they mutate real workspace state:

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

- `codex-responses-api-proxy` exists in official Codex source, but it reads
  `OPENAI_API_KEY` from stdin and forwards only `POST /v1/responses`; it is not
  an OAuth-only route.

## Generated Artifacts

- `artifacts/codex_oauth_image.png` — 1024x1024 PNG
- `artifacts/codex_oauth_drawing.png` — 1024x1024 PNG
- `artifacts/realtime_oauth_audio_response.pcm16` — Realtime audio output, PCM16
- `artifacts/realtime_oauth_audio_transcript.txt` — transcript: `oauth realtime ok`
- `artifacts/vision_probe_red_square.png` — local vision test input
- `artifacts/tiny_silence.wav` — local STT probe input
- `artifacts/codex_backend_upload_probe.txt` — local file used for the
  ChatGPT backend upload probe

## OAuth Surfaces That Were Blocked

These rejected the Codex OAuth token with missing-scope or secret-key-required
errors:

- `GET /v1/models`
- `GET /v1/files`
- `POST /v1/chat/completions`
- `POST /v1/completions`
- `POST /v1/responses`
- `POST /v1/responses` with `web_search_preview`
- `POST /v1/images/generations`
- `POST /v1/images/edits`
- `POST /v1/images/variations`
- `POST /v1/audio/speech`
- `POST /v1/audio/translations`
- `POST /v1/moderations`
- `GET /v1/vector_stores`
- `GET /v1/batches`
- `GET /v1/fine_tuning/jobs`
- `GET /v1/evals`
- `GET /v1/containers`
- `GET /v1/videos`
- `POST /v1/videos`
- `POST /v1/uploads`
- `GET /v1/assistants`
- `POST /v1/threads`
- `POST /v1/chatkit/sessions`
- Admin and organization endpoints:
  `projects`, `users`, `admin_api_keys`, `audit_logs`, `usage/completions`,
  and `costs`
- Codex backend direct `audio.speech` route

The older "files/uploads are local substitute only" result is now narrower:
official `/v1/files` and `/v1/uploads` are still blocked, but Codex/ChatGPT's
own `backend-api/files` route works with OAuth and returns a `sediment://...`
file URI plus a signed download URL.

The separate `https://chatgpt.com/api/codex/...` paths found in source were
also probed. On this deployment they returned HTML `404` or `302`; the live
equivalent for local Codex app use is the `backend-api/wham/...` family.

The newer `/backend-api/ps/plugins/...` workspace plugin service paths from the
current source were also probed read-only and returned `404` in this deployment.
The older `/backend-api/plugins/list`, `/plugins/featured`, and
`/plugins/export/curated` routes are the working plugin catalog routes here.

## Notes

OpenAI's public API docs still describe standard Platform authentication as
API-key based. The OAuth behavior above is empirical for this local
Codex/ChatGPT OAuth token and its current scopes. Treat it as account/scope
dependent, not a public guarantee.
