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
| Image edits | Codex vision over the source image plus image generation | Local substitute |
| Image variations | Codex vision over the source image plus image generation | Local substitute |
| Image drawing | Codex image generation tool | Usable |
| Basic TTS | Realtime WebSocket audio, PCM16 output | Usable |
| WebRTC voice call setup | `POST /v1/realtime/calls` multipart SDP | Native |
| Realtime call lifecycle | Local `/v1/realtime/calls/{call_id}/{accept,hangup,refer,reject}` state | Local substitute |
| Transcription | `POST /v1/audio/transcriptions` | Native |
| Audio translation | OAuth transcription plus Codex text translation | Local substitute |
| Audio voices | Built-in voice catalog plus local custom-voice metadata | Local substitute |
| Voice consents | Local consent recording metadata and file storage | Local substitute |
| Realtime transcription setup | `POST /v1/realtime/client_secrets` with `session.type="transcription"` | Native |
| Realtime session aliases | `/v1/realtime/sessions`, `/v1/realtime/transcription_sessions` over client secrets | Local proxy alias |
| Realtime translation setup | `POST /v1/realtime/translations/client_secrets` | Native |
| Embeddings | `POST /v1/embeddings` | Native |
| Files | `POST /backend-api/files` plus finalize/download probe | Native Codex/ChatGPT backend |
| Uploads | Local upload session/parts, completed through ChatGPT-backed file upload | Local proxy plus native Codex/ChatGPT backend |
| Batches | Local JSONL processor over supported local proxy routes | Local substitute |
| Vector stores | Local JSON vector store + OAuth embeddings | Local substitute |
| Evals | Local eval runner + Codex text | Local substitute |
| Fine-tuning grader run/validate | Local `string_check` and `multi` grader evaluator | Local preflight substitute |
| Moderation | Local keyword heuristic | Local substitute |
| Assistants | Local orchestration with Codex text/tools | Partial substitute |
| Conversations | Local conversation and item store | Local substitute |
| ChatKit | Local sessions, threads, and items | Local substitute |
| Skills | Installed Codex skill registry plus local skill bundles | Local substitute |
| Codex task/environment reads | `GET /backend-api/wham/tasks*`, `GET /backend-api/wham/environments` | Native ChatGPT backend read |
| Connector discovery | `GET /backend-api/connectors/directory/list*` | Native ChatGPT backend read |
| Plugin discovery | `GET /backend-api/plugins/list`, `/featured`, `/export/curated` | Native ChatGPT backend read |
| Apps MCP tools | `POST /backend-api/wham/apps` | Native ChatGPT backend MCP |
| Containers | Local container metadata and file storage | Local substitute |
| Fine-tuning jobs/checkpoints | Local job lifecycle, event, checkpoint, and permission metadata | Local substitute |
| Organization/Projects/Usage | Local admin/project/usage sandbox metadata | Local substitute |
| Videos | Local storyboard/job metadata, remix/edit/extension records, and JSON content manifests | Local substitute |
| ChatKit hosted sessions | No true hosted substitute without ChatKit API auth | Not covered |
| Hosted Skills | No true hosted substitute without Skills API auth | Not covered |
| Real hosted Admin/Usage | No substitute for account/org data or mutations | Not covered |

## Why This Distinction Matters

The blocked Platform endpoints did not become OAuth endpoints. The compatibility
layer just gives you the same workflow result where possible:

- text/chat goes through Codex OAuth
- image/drawing goes through Codex OAuth image generation
- image edits and variations use Codex vision to describe the source image,
  then Codex image generation to create a new image; the hosted OpenAI image
  edit/variation endpoints remain blocked by the OAuth token
- voice output goes through Realtime OAuth audio
- WebRTC call setup goes through the official Realtime calls route with OAuth
  when supplied a valid SDP offer
- Realtime call lifecycle endpoints record local state for app/SDK workflows;
  they do not prove hosted OpenAI accepted accept/hangup/refer/reject for a
  real call id
- realtime transcription setup goes through the current
  `/v1/realtime/client_secrets` transcription-session shape
- realtime translation setup goes through the official
  `/v1/realtime/translations/client_secrets` route
- transcription and embeddings use the official endpoints that accepted OAuth
- audio translation uses the official OAuth transcription route first, then
  Codex text translation; the hosted `/v1/audio/translations` route itself is
  still blocked by the OAuth token
- audio voice and voice-consent routes are local metadata stores for app
  workflow compatibility; hosted custom voice creation remains a Platform
  feature for eligible accounts
- files use the ChatGPT/Codex backend file route and return
  `sediment://file_...` URIs
- uploads are local OpenAI-style sessions; completion creates a ChatGPT-backed
  file
- batches are local JSONL jobs over supported local proxy routes
- moderation is a local keyword heuristic, not hosted OpenAI moderation
- assistants and threads are local stores plus Codex text for run output
- conversations are local metadata and item stores; this does not provide the
  hosted OpenAI conversation resource
- vector stores/evals are implemented locally
- fine-tuning jobs/checkpoints/permissions are local metadata stores for app
  workflow compatibility; hosted training, hosted fine-tuned model creation,
  and real checkpoint permission changes still need Platform/Admin credentials
- fine-tuning grader `run`/`validate` is implemented locally for `string_check`
  and `multi` graders only
- organization, project, usage, and cost routes return local sandbox metadata
  for SDK/app workflows; real users, keys, billing, usage, retention settings,
  and Admin mutations still need Platform/Admin credentials
- video routes return local job/storyboard metadata and JSON content manifests
  for SDK/app workflows; hosted Sora rendering, hosted MP4 bytes, and real video
  content retrieval still need Platform credentials and eligible hosted video
  access
- containers are local metadata directories plus file storage; this does not
  provide hosted OpenAI container execution
- ChatKit sessions/threads/items are local stores; this does not provide hosted
  ChatKit services
- Skills are local Codex skill discovery plus local bundle/version storage; this
  does not provide hosted OpenAI Skills deployment

Anything that must happen inside OpenAI's real server-side project resources
still needs the official API-key or Admin-key route.

The proxy supports an explicit hybrid fallback for those cases. With
`OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1`, `boundary` mode forwards only known
Platform/Admin boundary paths. `OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=prefer` or
the request header `X-OAuth-Compat-Prefer-Platform: 1` forwards official OpenAI
paths before local compatibility handlers. That is exact hosted API routing with
official credentials, not ChatGPT/Codex OAuth support.

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
python bridge.py serve --port 8787
```

Automated proxy smoke:

```bash
cd chatgpt-oauth-bridge
python bridge.py smoke --include-images
```

Drop `--include-images` when you want a faster non-image smoke.

OpenAI Python SDK smoke:

```bash
cd chatgpt-oauth-bridge
python bridge.py sdk-smoke --include-images
```

Release preflight:

```bash
cd chatgpt-oauth-bridge
python bridge.py preflight
```

Point a local client at `http://127.0.0.1:8787/v1`. It supports create-style
text/chat, local response retrieve/input-items/cancel/delete, local chat
completion retrieve/list/update/messages/delete, local assistant
create/list/retrieve/update/delete, local thread create/retrieve/update/delete,
local thread message create/list/retrieve/update/delete, local run
create/list/retrieve/update/cancel and run-step list/retrieve, `stream=true` SSE for
Responses and Chat Completions, embeddings, image generation, local moderation,
local audio voice catalog/consent metadata,
Realtime PCM16 speech, transcription, Realtime session aliases and call lifecycle state,
ChatGPT-backed file upload/list/retrieve/content/delete, local upload
create/parts/complete/cancel, local batch create/list/retrieve/output/cancel,
local video create/list/retrieve/delete/content/remix/edit/extension and
character metadata, local fine-tuning grader run/validate, local vector store create/list/retrieve/add/search/delete, local vector store file
create/list/retrieve/content/delete, local vector store file batch
create/retrieve/list-files/cancel, model retrieve, OpenAI-style local
evals/runs/output-items, and a direct text expectation eval helper. It also
handles browser CORS preflight with `OPTIONS /v1/*` and CORS headers on
responses. `GET /v1/oauth-capabilities` lets a local app show the honest
capability boundary before sending work. `GET /v1/oauth-route-policy` returns a
machine-readable allow/deny/fallback policy for every documented OpenAI path.
`GET /v1/oauth-quickstart` returns the same first-run bundle as
`python bridge.py quickstart`: env setup, CI gate, route policy, and the current
full-goal verdict.
`GET /v1/oauth-goal-audit` returns the same full-goal verdict as
`python bridge.py verdict`, including what is ready, what needs Platform/Admin
credentials, and what must not be claimed as OAuth support.
