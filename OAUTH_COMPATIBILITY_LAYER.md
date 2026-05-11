# OAuth Compatibility Layer

Yes: if the goal is "get the function done with OAuth only," the working OAuth
surfaces cover a lot more than the literal API table suggests.

The layer is:

- `src/oauth_feature_router.py`
- `src/oauth_openai_compat_server.py`
  for a local `/v1`-style HTTP surface

It routes blocked official API families to the closest working OAuth path:

| Desired function | OAuth-only implementation | Fidelity |
|---|---|---|
| Responses | Codex text response | Usable |
| Chat Completions | Codex text response over serialized messages | Usable |
| Image generation | Codex image generation tool | Usable |
| Image drawing | Codex image generation tool | Usable |
| Basic TTS | Realtime WebSocket audio, PCM16 output | Usable |
| WebRTC voice call setup | `POST /v1/realtime/calls` multipart SDP | Native |
| Transcription | `POST /v1/audio/transcriptions` | Native |
| Realtime transcription setup | `POST /v1/realtime/client_secrets` with `session.type="transcription"` | Native |
| Embeddings | `POST /v1/embeddings` | Native |
| Files | `POST /backend-api/files` plus finalize/download probe | Native Codex/ChatGPT backend |
| Uploads | Signed upload URL returned by `backend-api/files` | Native Codex/ChatGPT backend |
| Vector stores | Local JSON vector store + OAuth embeddings | Local substitute |
| Evals | Local eval runner + Codex text | Local substitute |
| Assistants | Local orchestration with Codex text/tools | Partial substitute |
| Codex task/environment reads | `GET /backend-api/wham/tasks*`, `GET /backend-api/wham/environments` | Native ChatGPT backend read |
| Connector discovery | `GET /backend-api/connectors/directory/list*` | Native ChatGPT backend read |
| Plugin discovery | `GET /backend-api/plugins/list`, `/featured`, `/export/curated` | Native ChatGPT backend read |
| Apps MCP tools | `POST /backend-api/wham/apps` | Native ChatGPT backend MCP |
| Containers | Local process/container execution outside OpenAI | Partial substitute |
| Fine-tuning | No true substitute | Not covered |
| ChatKit hosted sessions | No true hosted substitute without ChatKit API auth | Not covered |
| Admin/Usage | No substitute, account/org data required | Not covered |

## Why This Distinction Matters

The blocked Platform endpoints did not become OAuth endpoints. The compatibility
layer just gives you the same workflow result where possible:

- text/chat goes through Codex OAuth
- image/drawing goes through Codex OAuth image generation
- voice output goes through Realtime OAuth audio
- WebRTC call setup goes through the official Realtime calls route with OAuth
  when supplied a valid SDP offer
- realtime transcription setup goes through the current
  `/v1/realtime/client_secrets` transcription-session shape
- transcription and embeddings use the official endpoints that accepted OAuth
- files/uploads use the ChatGPT/Codex backend file route and return
  `sediment://file_...` URIs
- vector stores/evals are implemented locally

Anything that must happen inside OpenAI's server-side project resources still
needs the official API-key or Admin-key route.

The important file boundary: official Platform `/v1/files` and `/v1/uploads`
are still blocked by this OAuth token. The working route is Codex's
ChatGPT-backed file storage, the same route the official `openai/codex` repo
uses for Apps MCP file parameters.

## Smoke Test

```bash
cd chatgpt-oauth-bridge
python src/oauth_feature_router.py
```

Local `/v1` server smoke:

```bash
cd chatgpt-oauth-bridge
PYTHONPATH=src python src/oauth_openai_compat_server.py --port 8787
```

Point a local client at `http://127.0.0.1:8787/v1`. It supports
`/v1/responses`, `/v1/chat/completions`, `/v1/embeddings`, and
`/v1/images/generations` by routing to OAuth-backed implementations.
