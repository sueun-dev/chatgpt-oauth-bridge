# OAuth Results Summary

Current continuation note:

- Date: `2026-06-06`
- `python3 bridge.py smoke --include-images` passed `108/108` HTTP proxy
  checks in the latest local run.
- `python3 bridge.py sdk-smoke --include-images` passed `90/90` OpenAI Python
  SDK proxy checks in the latest local run.
- `PYTHONPATH=src python3 src/run_oauth_matrix.py` ran `53` OAuth-only probes:
  `12` pass, `35` expected_blocked, `4` not_available,
  `2` auth_accepted_request_invalid, and `0` fail.
- `python3 bridge.py audit` now classifies the current `172` documented OpenAI
  API paths as `4` direct official OAuth-verified paths, `167`
  local/ChatGPT-backend compatibility paths, `0` API-key/Admin-key required,
  `1` not available, `0` auth-reached-but-not-complete, and `0`
  resource-bound.
- Real Realtime voice WebSocket media and real `/v1/realtime/calls` are not
  verified OAuth-only paths in the current run. `/v1/realtime/calls` returned
  HTTP `500` on the direct OAuth probe, while the shape probe reached auth and
  returned HTTP `400` for the test payload.
- Official hosted `/v1/audio/speech` rejected the OAuth token with HTTP `401`;
  the local bridge `/v1/audio/speech` route is a compatibility fallback, not
  official hosted OpenAI TTS.
- `python bridge.py offline-smoke` passed `36` no-network/no-socket router checks:
  local Responses, Chat, Assistants/Threads run/steps, message delete,
  approximate Responses input-token estimates, local Responses compaction,
  local audio translation, local audio voice catalog/consent metadata,
  Realtime session aliases and call lifecycle state,
  local image edits/variations, local container files, local ChatKit sessions/threads/items, local Skills registry/bundles, local Conversations/items, legacy Completions, moderation, client config generation, status dashboard
  generation, templated official path classification/routing, local
  fine-tuning job/checkpoint/event/permission metadata, local
  fine-tuning grader run/validate for `string_check` and `multi`,
  local Organization/Project/Usage sandbox metadata, local video
  storyboard/job metadata and JSON content manifests,
  explicit Platform/Admin/API-access-token fallback disabled/enabled/prefer-mode
  routing decisions, vector search, and eval output shape.
- `python bridge.py readiness` writes `reports/readiness_latest.md` and currently
  reports `goal_complete=false` because this restricted environment cannot
  reach Codex model discovery and cannot bind localhost for live HTTP/SDK smoke.
- `python bridge.py classify <path>` queries `reports/openai_surface_audit_latest.json`
  for a single OpenAI API path, so users can quickly see whether a path is
  direct OAuth, local/ChatGPT-backend compatibility, or API-key/Admin-key only.
- `python bridge.py guide` writes `reports/compatibility_guide_latest.md/json`
  and groups all documented paths into user decisions: official OAuth verified,
  use local bridge, needs API/Admin key, needs live-resource proof, incomplete,
  or not routed here.
- `python bridge.py coverage` writes `reports/coverage_map_latest.md/json/csv`
  and groups all documented OpenAI paths by product area, such as `audio`,
  `realtime`, `fine_tuning`, `organization/admin`, and `vector_stores`, with a
  ready-vs-boundary decision for each group.
- `python bridge.py boundaries` writes `reports/boundary_playbook_latest.md/json`
  and turns any Platform/Admin/resource-bound paths into safe modes: strict
  OAuth-only gates, explicit Platform fallback commands, and Admin credential
  separation.
- `python bridge.py fallback` writes `reports/platform_fallback_latest.md/json`
  and shows the explicit Platform/Admin credential fallback state. The fallback
  is disabled by default; with `OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1`, routes
  can be forwarded to official OpenAI API using `OPENAI_API_KEY`,
  `OPENAI_ACCESS_TOKEN`, or `OPENAI_ADMIN_KEY` when they are still boundaries or
  when `prefer` mode intentionally chooses hosted behavior over local
  compatibility.
  `OPENAI_ACCESS_TOKEN` is for official OpenAI workload-identity-style bearer
  tokens, not a ChatGPT/Codex OAuth session token. This is hybrid routing, not
  OAuth support. The default mode is `boundary`; `OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=prefer`
  or `X-OAuth-Compat-Prefer-Platform: 1` makes hosted OpenAI API behavior take
  precedence over local compatibility handlers when a matching credential is
  present.
- `python bridge.py config` writes `reports/client_config_latest.md/json` with
  the local `base_url`, placeholder SDK key, Python SDK, JavaScript SDK, curl,
  environment variable, and metadata endpoint snippets users need to wire a
  local app to the bridge without guessing.
- `python bridge.py status` writes `reports/status_latest.md/json` and prints a
  one-screen dashboard: completion state, base URL, route-category counts,
  current model-discovery/localhost-bind state, smoke evidence, next actions,
  and local git change count.
- Report-style top-level commands now consistently pass `--no-write` through to
  their underlying scripts, including status, readiness, guide, config, audit,
  smoke, SDK smoke, and offline smoke. This lets users inspect current evidence
  without changing tracked reports.
- `python bridge.py doctor` writes `reports/doctor_latest.md/json` and separates
  package health from live environment readiness and full-goal completion.
  Default `doctor` can pass while `full_goal_complete=false`; `doctor --strict`
  exits non-zero unless package health, live environment, and full-goal
  readiness all pass.
- `python bridge.py live-check` writes `reports/live_check_latest.md/json` and
  is the launch gate for a normal local shell. It proves environment readiness,
  then runs HTTP proxy smoke, OpenAI Python SDK smoke, readiness, and strict
  doctor in one command. `reports/openai_bridge_launch_gate.sh` runs the same
  gate for users who want a script file next to the CI gate.
- `python bridge.py publish-check` writes `reports/publish_check_latest.md/json`
  and is the GitHub/clone-user gate. It shows whether local-only source files
  are still untracked and whether local `HEAD` matches the configured upstream
  branch.
- `reports/openai_bridge_publish_gate.sh --push` is the networked-shell publish
  gate: it runs no-write preflight, pushes the current branch, refreshes the
  local `origin/<branch>` ref, then runs strict no-write `publish-check`.
- If `git push` fails but `GITHUB_TOKEN` or `GH_TOKEN` is available, the publish
  gate falls back to `python bridge.py publish-api --branch <branch>`, which
  publishes the same clean local diff through the GitHub Git data API.
- `python bridge.py publish-api --dry-run` can now still produce a publish plan
  in a no-network shell by falling back to the local `origin/<branch>` tracking
  ref.
- In write mode, `publish-api` reads the remote branch ref and base tree through
  the GitHub API before creating the replacement tree and commit, avoiding stale
  local tracking refs.
- `publish-api` writes `reports/github_api_publish_plan_latest.md/json` unless
  `--no-write` is used, so the exact branch, local head, remote head, fallback
  source, and changed paths are inspectable after a dry-run.
- `python bridge.py finish --push` and `reports/openai_bridge_finish_gate.sh --push`
  are the end-to-end user gates: publish first, then live launch. They fail
  until GitHub, Codex/ChatGPT network access, and localhost bind evidence all
  pass in the same normal shell.
- `python bridge.py check ...` writes `reports/usage_check_latest.md/json` for
  a list of paths, full `api.openai.com` URLs, files, or directories. It detects
  REST path literals plus OpenAI Python and JS/TS SDK calls, then maps them to
  the same direct-OAuth/local-bridge/Platform-credential decisions. The current
  usage-scanner verifier maps SDK method forms to all `172` documented OpenAI
  API paths.
  Direct SDK method arguments such as `client.completions.create` are also
  accepted. Concrete resource URLs such as `/v1/videos/video_123/remix` now
  match the official audit template `/videos/{video_id}/remix`.
- `python bridge.py migrate ...` writes `reports/migration_plan_latest.md/json`
  for a local app or path list. It combines the usage scanner with the client
  config into one migration plan: local `OPENAI_BASE_URL`, placeholder SDK key,
  proxy start command, CI gate, ready routes, and any blocked/API-key-boundary
  routes.
- `python bridge.py verdict --strict` exits non-zero until the full-goal
  verdict is complete. Plain `python bridge.py verdict` remains a report command
  that exits successfully so package/route-policy gates can display the current
  go/no-go state without failing early.
- Official OpenAI docs currently describe Platform API authentication as bearer
  credentials from API keys or short-lived workload identity federation access
  tokens. The current audit has `0` API-key/Admin-key required paths because
  every documented path is now classified as either direct OAuth proof or an
  explicit local/ChatGPT-backend compatibility route. That still does not mean
  ChatGPT/Codex OAuth became a hosted Platform API credential.
- `python bridge.py audit` now falls back to the latest checked-in OpenAPI path
  list when the current environment cannot reach the official OpenAPI source.
  This restricted run reused the existing `172`-path list and reclassified the
  implemented local Assistants/Threads routes as local compatibility, not hosted
  OpenAI Assistants/Threads OAuth support.
- The official OpenAI Developer Docs endpoint index returned `172` paths under
  `https://api.openai.com/v1` on this pass, matching the local audit count. That
  confirms endpoint-count parity, not live hosted API behavior from this shell.
  Spot checks against the same official spec show `/v1/videos` using normal
  `OPENAI_API_KEY` examples and `/v1/organization/projects` using
  `AdminApiKeyAuth` / `OPENAI_ADMIN_KEY`.
- `python bridge.py env` writes `reports/environment_latest.md`. In this
  restricted run, it records Codex model discovery as unreachable and localhost
  binding as blocked, so live HTTP/SDK smoke cannot be refreshed here.
- `python bridge.py preflight` now records the current environment, runs
  `offline-smoke`, checks route manifest/docs consistency, regenerates the
  surface audit and readiness report, and checks representative direct-OAuth,
  local-compatibility, and API-key-boundary path classifications as part of the
  release gate. It also regenerates the compatibility guide and a representative
  coverage map, client config, platform fallback status, status dashboard,
  doctor report, summary count consistency, SDK usage-scanner coverage, usage
  check, and migration plan. It passed after these changes.
  It is intentionally a package/report gate; live launch evidence comes from
  `python bridge.py live-check`.

Last full run:

- Time: `2026-06-06T13:29:50Z` to `2026-06-06T13:32:30Z`
- Runtime auth source: `~/.codex/auth.json` Codex CLI OAuth token
- No `OPENAI_API_KEY`, `OPENAI_ACCESS_TOKEN`, or `OPENAI_ADMIN_KEY` was present
  in the test process.
- Full report: `reports/latest.md`
- Surface audit: `reports/openai_surface_audit_latest.md`
- Scope: `53` OAuth-only probes across Codex, text, vision, image, audio,
  Realtime, embeddings, legacy completions, Responses tools, files/uploads,
  vector stores, batches, fine-tuning, evals, skills, containers, videos,
  Assistants, conversations, ChatKit, custom voices, and Admin/Usage probes.

Status counts:

- `pass`: 12
- `expected_blocked`: 35
- `not_available`: 4
- `auth_accepted_request_invalid`: 2
- `fail`: 0

Official API surface audit:

- `172` documented OpenAI API paths parsed
- `4` direct official OAuth-verified paths
- `167` local/ChatGPT-backend compatibility paths
- `0` API-key/Admin-key required paths
- `1` not available
- `0` auth-reached-but-not-complete paths
- `0` resource-bound paths

Local proxy smoke:

- Time: `2026-06-06T13:27:51Z`
- Full report: `reports/proxy_smoke_latest.md`
- `pass`: 108
- Covered: health, capabilities, browser CORS preflight, models, responses,
  response retrieve/input-items/cancel/delete, chat completions, chat
  retrieve/list/update/messages/delete, clean 400 bad-request handling,
  responses/chat SSE streaming, embeddings, image generation, local moderation, file
  list/upload/retrieve/content/delete, OpenAI-style uploads
  create/parts/complete/cancel, local batch create/list/retrieve/output/cancel,
  audio transcription, model retrieve, vector store create/list/retrieve/add/search/delete,
  vector store file create/list/retrieve/content/delete, vector store file batch
  create/retrieve/list-files/cancel, direct local eval, OpenAI-style
  eval/create/list/retrieve/update/run/output-item/cancel/delete, and Realtime
  PCM16 speech.

OpenAI Python SDK proxy smoke:

- Time: `2026-06-06T13:29:42Z`
- Full report: `reports/openai_sdk_proxy_smoke_latest.md`
- `pass`: 90
- Covered through the official `openai` Python package with
  `base_url=http://127.0.0.1:<port>/v1`: models, responses, chat completions,
  response retrieve/input-items/cancel/delete, chat
  retrieve/list/update/messages/delete, responses/chat streaming, embeddings, moderations, batch
  create/list/retrieve/output/cancel, uploads create/part/complete/cancel, eval
  create/list/retrieve/update/run/output-item/cancel/delete, file
  create/retrieve/content/list/delete, vector store create/list/retrieve/delete,
  vector store file create/list/retrieve/content/delete, vector store file batch
  create/retrieve/list-files/cancel, audio transcription, audio speech, and image
  generation.

Release preflight:

- Command: `.venv/bin/python bridge.py preflight`
- Result: `pass`
- Covered: environment probe, offline router smoke, route manifest/docs
  consistency, surface audit regeneration, compatibility guide generation, client
  config generation, status dashboard generation, usage compatibility check
  generation, readiness report generation, representative path classification,
  compileall, `git diff --check`, required checked-in report presence, summary
  count consistency, and local source/doc secret scan.

Last deep backend run:

- Time: `2026-05-29T21:56:06Z` to `2026-05-29T21:56:38Z`
- Full report: `reports/deep_oauth_research_latest.md`
- Apps MCP tool inventory: `reports/codex_apps_tools_latest.md`
- `openai/codex` source HEAD checked: `4859d80ffeec76cc59c95fd274157c6b5560b4d2`
- Scope: focused ChatGPT/Codex backend routes from the official `openai/codex`
  repo plus the Realtime WebRTC call shape and source-backed side-effect
  routes.

Deep status counts:

- `pass`: 30
- `auth_accepted_request_invalid`: 19
- `expected_blocked`: 1
- `not_run_side_effect`: 6
- `not_run_no_candidate`: 2
- `not_oauth_api_key_proxy`: 1

## OAuth Surfaces That Worked

Codex/ChatGPT OAuth backend:

- Model discovery through `https://chatgpt.com/backend-api/codex`
- Text response with `gpt-5.5`
- Vision input with `gpt-5.5`
- Image generation through the Codex Responses `image_generation` tool
- Drawing generation through the same image tool
- Remote compaction through `POST /backend-api/codex/responses/compact`
- ChatGPT backend file upload/finalize/download through
  `POST /backend-api/files` and `POST /backend-api/files/{file_id}/uploaded`
- ChatGPT plugin catalog reads through `GET /backend-api/plugins/list`
  (`127` items), `GET /backend-api/plugins/featured?platform=codex`
  (`41` items), and `platform=chat` (`19` items)
- ChatGPT connector directory reads through
  `GET /backend-api/connectors/directory/list` and
  `GET /backend-api/connectors/directory/list_workspace` (`1347` apps each in
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
- Realtime transcription client secret via `POST /v1/realtime/client_secrets`
  with `session.type="transcription"`. The local proxy exposes
  `/v1/realtime/transcription_sessions` as a compatibility alias over that
  OAuth-accepted client-secret route.
- Realtime translation client secret via
  `POST /v1/realtime/translations/client_secrets`.
- `POST /v1/embeddings`
- `POST /v1/conversations` reached route validation, but the current probe
  stopped at `Project ID must be set for the request`; it is not counted as a
  complete OAuth replacement.

Realtime paths that are not verified OAuth-only in the current run:

- Realtime WebSocket media is marked `not_available`.
- `POST /v1/realtime/calls` returned HTTP `500` on the direct OAuth probe. The
  shape probe reached auth but returned HTTP `400` for the test payload, so it
  is not counted as a working Realtime voice/call path.

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
- `artifacts/realtime_oauth_audio_response.pcm16` — previous Realtime audio
  output artifact; the current matrix does not count Realtime WebSocket media as
  verified OAuth-only.
- `artifacts/realtime_oauth_audio_transcript.txt` — previous transcript
  artifact; the current matrix does not count Realtime WebSocket media as
  verified OAuth-only.
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
- `POST /v1/responses/input_tokens`
- `POST /v1/images/generations`
- `POST /v1/images/edits`
- `POST /v1/images/variations`
- `POST /v1/audio/speech`
- `POST /v1/audio/translations`
- `POST /v1/moderations`
- `GET /v1/vector_stores`
- `GET /v1/batches`
- `/v1/organization/*`
- `/v1/projects/{project_id}/*`
- `GET /v1/fine_tuning/jobs`
- `POST /v1/fine_tuning/jobs`
- `GET /v1/fine_tuning/jobs/{fine_tuning_job_id}`
- `POST /v1/fine_tuning/jobs/{fine_tuning_job_id}/cancel`
- `GET /v1/fine_tuning/jobs/{fine_tuning_job_id}/checkpoints`
- `GET /v1/fine_tuning/jobs/{fine_tuning_job_id}/events`
- `POST /v1/fine_tuning/jobs/{fine_tuning_job_id}/pause`
- `POST /v1/fine_tuning/jobs/{fine_tuning_job_id}/resume`
- `GET /v1/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions`
- `POST /v1/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions`
- `DELETE /v1/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions/{permission_id}`
- `GET /v1/evals`
- `GET /v1/skills`
- `GET /v1/containers`
- `GET /v1/videos`
- `GET /v1/videos/{video_id}`
- `GET /v1/videos/{video_id}/content`
- `GET /v1/videos/characters`
- `GET /v1/videos/characters/{character_id}`
- `POST /v1/videos`
- `POST /v1/videos/{video_id}/remix`
- `POST /v1/videos/edits`
- `POST /v1/videos/extensions`

The local proxy now has a separate `/v1/audio/translations` compatibility route:
it runs OAuth audio transcription first, then translates the transcript to
English with Codex text. That does not change the direct official
`POST /v1/audio/translations` OAuth result above, which still rejected the token
in the latest matrix.

The local proxy also has `/v1/images/edits` and `/v1/images/variations`
compatibility routes: they describe the source image with Codex vision and then
generate a new image with Codex image generation. The hosted OpenAI image edit
and variation endpoints above still rejected the OAuth token in the latest
matrix.

The local proxy also has `/v1/containers` compatibility routes for local
container metadata and file storage. Hosted OpenAI containers still require
Platform API credentials, but SDK/apps can use local create/retrieve/delete and
container file upload/list/retrieve/content flows for local workflows.

The local proxy also has `/v1/chatkit` compatibility routes for local sessions,
threads, and thread items. Hosted ChatKit still requires Platform API
credentials, but SDK/apps can use local create/retrieve/list/cancel flows while
staying inside the OAuth bridge.

The local proxy also has `/v1/skills` compatibility routes for installed Codex
skills and local skill bundles. Hosted OpenAI Skills still require Platform API
credentials, but SDK/apps can use local list/retrieve/content/version
create/delete flows for local workflows.

The local proxy also has `/v1/conversations` compatibility routes for local
conversation metadata and items. Hosted OpenAI Conversations still require
Platform API credentials for the real server resource, but SDK/apps can use
local create/retrieve/update/delete and item list/retrieve/delete flows.

The local proxy also has `/v1/realtime/sessions` and
`/v1/realtime/transcription_sessions` compatibility aliases. Both call the
OAuth-accepted `/v1/realtime/client_secrets` route and return session-shaped
client secret responses; they are not marked as direct hosted-route OAuth proof.
It also records local lifecycle state for
`/v1/realtime/calls/{call_id}/accept`, `/hangup`, `/refer`, and `/reject` so
SDK/apps can exercise call-control flows without pretending those hosted
lifecycle mutations were proven with this OAuth token.

The local proxy also has `/v1/audio/voices` and `/v1/audio/voice_consents`
compatibility routes for built-in voice catalog metadata and local custom-voice
consent/voice records. Hosted custom voice creation is still an eligible
Platform-account feature, not ChatGPT/Codex OAuth support.

The local proxy also has `/v1/fine_tuning/jobs` and
`/v1/fine_tuning/checkpoints/.../permissions` compatibility routes for local
job lifecycle, event, checkpoint, and permission metadata. Hosted fine-tuning
training, hosted fine-tuned model creation, and real organization checkpoint
permission changes still require Platform/Admin credentials.
- `POST /v1/uploads`
- `GET /v1/assistants`
- `POST /v1/threads`
- `POST /v1/chatkit/sessions`
- `GET /v1/chatkit/threads`
- `GET /v1/audio/voice_consents`
- `POST /v1/audio/voices`
- Local Organization/Project/Usage sandbox endpoints:
  `projects`, `users`, `admin_api_keys`, `audit_logs`, `usage/completions`,
  and `costs`
- Codex backend direct `audio.speech` route

The older "files/uploads are local substitute only" result is now narrower:
official `/v1/files` and `/v1/uploads` are still blocked, but Codex/ChatGPT's
own `backend-api/files` route works with OAuth and returns a `sediment://...`
file URI plus a signed download URL. The local `/v1/uploads` proxy now supports
OpenAI-style create/part/complete/cancel; completing a local upload creates a
ChatGPT-backed file.

The separate `https://chatgpt.com/api/codex/...` paths found in source were
also probed. On this deployment they returned HTML `404` or `302`; the live
equivalent for local Codex app use is the `backend-api/wham/...` family.

The `/backend-api/ps/plugins/...` list/installed/shared workspace plugin routes
were also probed read-only and returned `200` with no plugin candidates in this
account snapshot. The older `/backend-api/plugins/list`, `/plugins/featured`,
and `/plugins/export/curated` routes are still the broad working plugin catalog
routes here.

## Notes

OpenAI's public API docs still describe standard Platform authentication as
API-key based. The OAuth behavior above is empirical for this local
Codex/ChatGPT OAuth token and its current scopes. Treat it as account/scope
dependent, not a public guarantee.
