# Legal OAuth Workarounds

This is the practical map after the extra source search and live probes.

Boundary used here:

- Use only this machine's own Hermes/Codex/ChatGPT OAuth token.
- Use OpenAI-owned public clients, official docs, and the public `openai/codex`
  source as route evidence.
- Do not bypass another user's data, workspace permissions, billing, rate
  limits, or admin boundaries.
- Do not run write/installation/enrollment routes automatically unless the user
  explicitly asks for that specific side effect.

## Best Working Substitutes

| Feature wanted | OAuth-only route that works now | Current evidence |
|---|---|---|
| Responses / chat | `POST /backend-api/codex/responses` | direct text pass |
| Vision input | `POST /backend-api/codex/responses` with `input_image` | vision pass in matrix |
| Image / drawing | Codex Responses `image_generation` tool with `gpt-image-2` | PNG artifacts generated |
| TTS / voice output | Realtime WebSocket response audio | PCM16 artifact generated |
| WebRTC voice call setup | `POST /v1/realtime/calls` multipart with SDP + session | `201`, answer SDP returned |
| STT | `POST /v1/audio/transcriptions` | pass |
| Realtime transcription | `POST /v1/realtime/client_secrets` with `session.type="transcription"` | pass |
| Embeddings | `POST /v1/embeddings` | pass |
| Files / uploads | `POST /backend-api/files` + signed upload + finalize | returns `sediment://file_...` |
| Vector search / RAG | local vector store + OAuth embeddings | compatibility layer smoke passed |
| Evals | local eval runner + Codex text | compatibility layer smoke passed |
| Connectors / tools | Apps MCP through `POST /backend-api/wham/apps` | `tools/list` returned 111 tools |
| Public GitHub search | Apps MCP `tools/call github_search_repositories` | safe public search passed |
| Connector discovery | `GET /backend-api/connectors/directory/list*` | 892 apps in latest run |
| Plugin discovery/export | `GET /backend-api/plugins/list`, `featured`, `export/curated` | pass |
| ChatGPT account/user shape | `GET /backend-api/me`, `GET /backend-api/accounts/check/...` | pass, sensitive values redacted |
| Browser Use site status | `GET /backend-api/aura/site_status` | pass |
| Codex usage | `GET /backend-api/wham/usage` | pass |
| Codex cloud tasks | `GET /backend-api/wham/tasks/list` | pass |
| Codex environments | `GET /backend-api/wham/environments` | pass |
| Repo environments | `GET /backend-api/wham/environments/by-repo/...` | pass |
| Agent identity JWKS | `GET /backend-api/wham/agent-identities/jwks` | pass |

The older `POST /v1/realtime/transcription_sessions` path now returns
`400 Unknown beta requested: 'realtime'` here. The current working transcription
setup is the `client_secrets` route with a transcription session object, which
matches the current OpenAI Realtime transcription docs.

## New Finding

`/v1/realtime/calls` is no longer just "auth accepted but invalid payload".
With Codex-style multipart form-data and a realistic WebRTC offer, this account's
Codex OAuth token got:

- HTTP `201`
- `Location: /v1/realtime/calls/calls/<call-id>`
- answer SDP body, 40 lines

That makes WebRTC call setup a real OAuth-capable path here. The wrapper exposes
it as `OpenAIOAuthAccess.realtime_webrtc_call_offer(offer_sdp, ...)`. For a real
browser app, pass the SDP from `RTCPeerConnection.createOffer()`.

## Source-Backed But Not Auto-Run

These are legal own-account routes found in the current `openai/codex` source,
but I did not execute them because they mutate real workspace state.

| Capability | Route | Why not auto-run |
|---|---|---|
| Create a Codex cloud task | `POST /backend-api/wham/tasks` | creates a real task |
| Remote app-server control | `POST /backend-api/wham/remote/control/server/enroll`; `WSS /backend-api/wham/remote/control/server` | enrolls/controls an environment |
| Share/update workspace plugin | `POST /backend-api/public/plugins/workspace/upload-url`; `POST /backend-api/public/plugins/workspace` | publishes workspace plugin share |
| Update/delete workspace plugin share | `POST /backend-api/public/plugins/workspace/{remote_plugin_id}`; `PUT /backend-api/ps/plugins/{remote_plugin_id}/shares`; `DELETE /backend-api/public/plugins/workspace/{remote_plugin_id}` | changes workspace share state |
| Install/uninstall plugin | `POST /backend-api/ps/plugins/{plugin_id}/install`; `POST /backend-api/plugins/{plugin_id}/uninstall` | changes installed plugin state |
| Add-credit nudge email | `POST /backend-api/wham/accounts/send_add_credits_nudge_email`; `POST /api/codex/accounts/send_add_credits_nudge_email` | sends real account email |
| Codex analytics | `POST /backend-api/codex/analytics-events/events` | telemetry write, not app capability |

If you want to test any of those, do it as an explicit one-off because they will
change the account/workspace.

## Still Not Legally Replaceable With This OAuth Token

These are account/project/admin server resources, not just "model capability":

- real OpenAI Platform fine-tuning jobs
- OpenAI-hosted `/v1/files`, `/v1/uploads`, `/v1/vector_stores`
- Admin/Usage organization endpoints
- hosted ChatKit session creation
- OpenAI containers/video resources
- official `/v1/responses`, `/v1/chat/completions`, `/v1/images/*`,
  `/v1/audio/speech` with the exact public endpoint
- official `codex-responses-api-proxy` as OAuth. It exists, but its own README
  says it reads `OPENAI_API_KEY` from stdin and forwards `/v1/responses`.

For app features, the substitutes above cover most of the behavior. For Platform
resources inside an OpenAI API organization, API key/Admin key is still the
legitimate boundary.

## Local `/v1` Compatibility Proxy

For local apps that expect an OpenAI-shaped base URL, this repo now includes:

```text
src/oauth_openai_compat_server.py
```

It is not an OpenAI-hosted endpoint. It runs on `127.0.0.1` and maps:

- `/v1/responses` -> Codex OAuth text
- `/v1/chat/completions` -> Codex OAuth text over serialized messages
- `/v1/embeddings` -> OAuth `/v1/embeddings`
- `/v1/images/generations` -> Codex OAuth image generation

Smoke test on `2026-05-11`: `/health`, `/v1/responses`,
`/v1/chat/completions`, and `/v1/embeddings` all returned `200`.

## Source Links

- Codex OAuth authentication: `https://developers.openai.com/codex/auth`
- OpenAI API authentication boundary: `https://platform.openai.com/docs/api-reference/authentication`
- Realtime WebRTC: `https://platform.openai.com/docs/guides/realtime-webrtc`
- MCP and connectors: `https://platform.openai.com/docs/guides/tools-remote-mcp`
- Public source searched: `https://github.com/openai/codex`
