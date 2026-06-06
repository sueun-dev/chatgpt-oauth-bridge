# ChatGPT OAuth Bridge

Use a real ChatGPT/Codex OAuth session for OpenAI-adjacent workflows without an `OPENAI_API_KEY`.

This project maps what currently works with a user-owned Codex/ChatGPT OAuth token, wraps the usable routes, and exposes a small local OpenAI-shaped compatibility server for apps that expect `/v1/...` endpoints.

It is not an official OpenAI SDK and it does not bypass authorization. If a route rejects the OAuth token, the test runner records that boundary instead of pretending it worked.

## What Works

Confirmed on the latest local run:

- Codex text responses
- Codex vision input
- Codex image and drawing generation
- Official `/v1/audio/transcriptions`
- Official `/v1/embeddings`
- Official Realtime client secrets
- Realtime WebSocket audio output
- Realtime transcription client secrets and local session aliases
- Realtime translation client secrets
- Realtime WebRTC call setup with a real SDP offer
- Local Realtime call lifecycle state for accept/hangup/refer/reject
- Local audio voice catalog and voice consent/custom voice metadata
- ChatGPT/Codex backend file upload
- ChatGPT plugin and connector catalog reads
- Codex task/environment metadata reads
- Codex Apps MCP discovery and read-only public GitHub search
- Local files, upload sessions, batches, vector stores, moderations, evals,
  fine-tuning job/checkpoint metadata, fine-tuning grader preflight,
  Assistants, Threads, Conversations, Skills, containers, Audio custom-voice
  metadata, ChatKit, video storyboard/job metadata, and
  Organization/Project/Usage sandbox compatibility layers
- Local `/v1` proxy for models, skills, responses, response compaction, legacy completions, chat completions, embeddings,
  images, speech, transcriptions/translations, Realtime session aliases and call lifecycle state, files, uploads, batches, vector stores,
  moderations, fine-tuning jobs/checkpoints, fine-tuning grader run/validate,
  Assistants/Threads, Organization/Project/Usage sandbox routes, video
  storyboard/content-manifest routes, and local eval helpers

Latest official API surface audit:

- `172` documented OpenAI API paths parsed
- `5` direct official OAuth-verified paths
- `167` local/ChatGPT-backend compatibility paths
- `0` API-key/Admin-key required paths
- `0` not available in this deployment
- `0` auth-reached-but-not-complete paths
- `0` resource-bound paths

Known boundaries:

- The audit no longer has an unclassified API/Admin-key-required bucket, but
  that does not make ChatGPT/Codex OAuth a hosted OpenAI Platform credential.
  OpenAI Platform `/v1/responses`, `/v1/chat/completions`, `/v1/images/...`,
  `/v1/audio/speech`, `/v1/files`, hosted batches, hosted vector stores,
  hosted fine-tuning training and real checkpoint permission changes, hosted
  evals, hosted video/Sora rendering, hosted containers, hosted
  Assistants/Threads, hosted ChatKit, hosted Skills, and real Admin/Usage data
  or mutations still need official Platform/Admin credentials when you need the
  real hosted server-side resource.
- Some features are handled honestly through local compatibility layers, for example Realtime session aliases through OAuth `/v1/realtime/client_secrets`, local Realtime call lifecycle state, local Conversations/items, local Skills registry/bundles, local ChatKit sessions/threads/items, local container metadata/files, local image edits/variations via Codex vision plus image generation, local audio translation via OAuth transcription plus Codex text, local audio voice catalog/consent metadata, local upload sessions, local batch processing, local vector stores plus OAuth embeddings, local heuristic moderation, local fine-tuning job/checkpoint/event/permission metadata, local Organization/Project/Usage sandbox metadata, local video storyboard/job metadata plus JSON content manifests, local fine-tuning grader preflight for `string_check`/`multi`, local Assistants/Threads orchestration, and local evals.
- Official hosted OpenAI API access should use documented Platform bearer credentials: API keys, Admin API keys for admin surfaces, or official workload identity federation access tokens where applicable. This repo does not convert a ChatGPT/Codex OAuth session into a general hosted Platform credential.

## Install

```bash
git clone https://github.com/sueun-dev/chatgpt-oauth-bridge.git
cd chatgpt-oauth-bridge

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The repo is kept Python 3.9-compatible on this Mac. `bridge.py` also sets a
local pycache directory for child checks so macOS sandboxed Python does not try
to write compile artifacts under `~/Library/Caches`.

## First Run: Generate The Surface Audit

On a fresh clone, run the audit once before the surface-aware commands:

```bash
python bridge.py audit
```

This writes `reports/openai_surface_audit_latest.json`, which several commands
read. That JSON report is gitignored (see `.gitignore`: `reports/*.json`), so a
clean clone does not ship it and must build it locally first. Until you run
`audit`, the commands that depend on this file fail with a
`Missing surface audit report` / `FileNotFoundError`, and the proxy route
`GET /v1/oauth-classify` returns `404` instead of a classification.

Commands and routes that require the audit to have been run first:
`quickstart`, `classify`, `coverage`, `policy`, `guide`, `check`, `migrate`,
`boundaries`, and the proxy's `/v1/oauth-classify`, `/v1/oauth-coverage-map`,
`/v1/oauth-route-policy`, `/v1/oauth-compatibility-guide`,
`/v1/oauth-boundary-playbook`, and `/v1/oauth-quickstart` routes. `audit` runs
automatically as the first step of `python bridge.py preflight`, so once a
preflight has succeeded the file is present and these commands work.

## Connect OAuth In One Check

Run the setup checker first:

```bash
python bridge.py setup
```

If dependencies are missing, it prints the exact `venv` and `pip install` commands. If OAuth is missing, it prints the exact login commands. If OAuth is ready, it prints the selected token source, visible model count, chosen text/image models, and a tiny text smoke result.

For a quick local readiness check before using the bridge:

```bash
python bridge.py doctor
python bridge.py doctor --strict
python bridge.py quickstart
python bridge.py publish-check
python bridge.py live-check
```

`quickstart` reads the surface audit, so on a fresh clone run
`python bridge.py audit` first (see [First Run](#first-run-generate-the-surface-audit))
or it fails with a missing-report error.

Default `doctor` exits successfully when the local package health checks pass,
but it still prints whether the full OpenAI API OAuth goal is incomplete.
`--strict` exits non-zero unless package health, live network/localhost
environment, and full-goal readiness all pass.
`quickstart` writes the first-run bundle users actually need: env example, CI
gate, launch gate, route policy, client config, and the current full-goal
verdict.
`live-check` is the launch gate for a normal local shell: it runs environment,
HTTP proxy smoke, OpenAI Python SDK smoke, readiness, and strict doctor checks
in one command.
`publish-check` is the GitHub/clone-user gate. It reports whether the local
source tree is committed and whether local `HEAD` matches the configured
upstream branch, so local-only files like `bridge.py` cannot be mistaken for
published user-facing functionality.

## Connect OAuth Manually

Use either Codex CLI or Hermes. Codex CLI is the cleanest path because this repo can read the live Codex OAuth session from `~/.codex/auth.json`.

### Option A: Codex CLI

```bash
codex login --device-auth
codex login status
```

Finish the browser/device-code login with your own ChatGPT/Codex account. The local token file should be:

```text
~/.codex/auth.json
```

### Option B: Hermes openai-codex

```bash
hermes login --provider openai-codex
hermes auth status openai-codex
```

The local token file should be:

```text
~/.hermes/auth.json
```

The wrapper checks both sources and chooses a usable OAuth token. Tokens stay local and are used only in memory.

## Quick Check

```bash
python bridge.py setup
python bridge.py info
```

You should see a JSON summary with the runtime source, Codex backend URL, selected models, and working method names.

Try a text call:

```bash
PYTHONPATH=src python - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
print(oauth.codex_text("Reply exactly: OAuth connected"))
PY
```

Generate an image:

```bash
PYTHONPATH=src python - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
path = oauth.codex_generate_image(
    "A clean product-style icon of an OAuth bridge, white background, no text",
    "artifacts/example_image.png",
)
print(path)
PY
```

Create an embedding:

```bash
PYTHONPATH=src python - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.official_embedding("OAuth embedding example")
print(len(res["data"][0]["embedding"]))
PY
```

More examples are in [`USAGE_EXAMPLES.md`](USAGE_EXAMPLES.md).

## Local OpenAI-Compatible Proxy

Start the proxy:

```bash
python bridge.py serve --port 8787
```

Point a local app to:

```text
http://127.0.0.1:8787/v1
```

Browser-based local apps can call the proxy directly. Responses include CORS
headers, and preflight `OPTIONS` requests return `204`.
Use `GET /v1/oauth-capabilities` for route-level capability metadata and
`GET /v1/oauth-readiness` for the current full-goal readiness summary.
Use `GET /v1/oauth-compatibility-guide` when a local app needs the same
user-facing direct/local/API-key route decision guide as `python bridge.py guide`.
Use `GET /v1/oauth-client-config` when a local app needs SDK/curl/env setup
metadata for the bridge base URL.
Use `GET /v1/oauth-quickstart` when a local app needs the same first-run bundle
as `python bridge.py quickstart`.
Use `GET /v1/oauth-coverage-map` when a local app needs product-group coverage
for direct OAuth, local bridge, and Platform-credential boundaries.
Use `GET /v1/oauth-route-policy` when a local app or CI job needs a
machine-readable allow/deny/fallback policy for all documented OpenAI paths.
Use `GET /v1/oauth-boundary-playbook` when a local app needs safe-mode commands
and per-group fallback/disable decisions for the remaining Platform/Admin
boundaries.
Use `GET /v1/oauth-status` for the one-screen readiness/config/next-action
dashboard that backs `python bridge.py status`.
Use `GET /v1/oauth-goal-audit` for the full-goal verdict that backs
`python bridge.py verdict`: complete API support, safe workarounds, user
readiness, and what must not be claimed.
Use `GET /v1/oauth-classify?path=/v1/embeddings` for a single route decision.
The surface-aware routes (`/v1/oauth-classify`, `/v1/oauth-coverage-map`,
`/v1/oauth-route-policy`, `/v1/oauth-compatibility-guide`,
`/v1/oauth-boundary-playbook`, `/v1/oauth-quickstart`) read the surface audit,
so on a fresh clone run `python bridge.py audit` first; otherwise they return
`404` until the report exists.
Known official OpenAI paths that are not implemented by the local bridge return
a structured `oauth_compat.boundary` JSON error instead of a generic `404`, so
SDK/app logs can show whether the route needs Platform credentials, live
resource proof, or a disabled fallback.

Supported routes:

```text
OPTIONS /v1/*
GET  /health
GET  /v1/oauth-capabilities
GET  /v1/oauth-readiness
GET  /v1/oauth-compatibility-guide
GET  /v1/oauth-client-config
GET  /v1/oauth-quickstart
GET  /v1/oauth-coverage-map
GET  /v1/oauth-route-policy
GET  /v1/oauth-boundary-playbook
GET  /v1/oauth-status
GET  /v1/oauth-goal-audit
GET  /v1/oauth-classify?path=/v1/embeddings
GET  /v1/models
GET  /v1/models/{model}
GET  /v1/skills
POST /v1/skills
GET  /v1/skills/{skill_id}
POST /v1/skills/{skill_id}
DELETE /v1/skills/{skill_id}
GET  /v1/skills/{skill_id}/content
GET  /v1/skills/{skill_id}/versions
POST /v1/skills/{skill_id}/versions
GET  /v1/skills/{skill_id}/versions/{version}
DELETE /v1/skills/{skill_id}/versions/{version}
GET  /v1/skills/{skill_id}/versions/{version}/content
GET  /v1/containers
GET  /v1/containers/{container_id}
DELETE /v1/containers/{container_id}
GET  /v1/containers/{container_id}/files
GET  /v1/containers/{container_id}/files/{file_id}
GET  /v1/containers/{container_id}/files/{file_id}/content
GET  /v1/chatkit/threads/{thread_id}
GET  /v1/chatkit/threads/{thread_id}/items
POST /v1/conversations
GET  /v1/conversations/{conversation_id}
POST /v1/conversations/{conversation_id}
DELETE /v1/conversations/{conversation_id}
GET  /v1/conversations/{conversation_id}/items
POST /v1/conversations/{conversation_id}/items
GET  /v1/conversations/{conversation_id}/items/{item_id}
DELETE /v1/conversations/{conversation_id}/items/{item_id}
GET  /v1/assistants
GET  /v1/assistants/{assistant_id}
DELETE /v1/assistants/{assistant_id}
GET  /v1/threads/{thread_id}
DELETE /v1/threads/{thread_id}
GET  /v1/threads/{thread_id}/messages
GET  /v1/threads/{thread_id}/messages/{message_id}
DELETE /v1/threads/{thread_id}/messages/{message_id}
GET  /v1/threads/{thread_id}/runs
GET  /v1/threads/{thread_id}/runs/{run_id}
GET  /v1/threads/{thread_id}/runs/{run_id}/steps
GET  /v1/threads/{thread_id}/runs/{run_id}/steps/{step_id}
GET  /v1/responses/{response_id}
GET  /v1/responses/{response_id}/input_items
DELETE /v1/responses/{response_id}
POST /v1/responses/compact
POST /v1/responses/input_tokens
POST /v1/completions
GET  /v1/chat/completions
GET  /v1/chat/completions/{completion_id}
GET  /v1/chat/completions/{completion_id}/messages
DELETE /v1/chat/completions/{completion_id}
GET  /v1/files
GET  /v1/files/{file_id}
GET  /v1/files/{file_id}/content
DELETE /v1/files/{file_id}
GET  /v1/batches
GET  /v1/batches/{batch_id}
GET  /v1/videos
GET  /v1/videos/{video_id}
GET  /v1/videos/{video_id}/content
GET  /v1/videos/characters
GET  /v1/videos/characters/{character_id}
GET  /v1/evals
GET  /v1/evals/{eval_id}
GET  /v1/evals/{eval_id}/runs
GET  /v1/evals/{eval_id}/runs/{run_id}
GET  /v1/evals/{eval_id}/runs/{run_id}/output_items
GET  /v1/evals/{eval_id}/runs/{run_id}/output_items/{output_item_id}
DELETE /v1/evals/{eval_id}
DELETE /v1/evals/{eval_id}/runs/{run_id}
GET  /v1/vector_stores
GET  /v1/vector_stores/{vector_store_id}
DELETE /v1/vector_stores/{vector_store_id}
GET  /v1/vector_stores/{vector_store_id}/file_batches/{batch_id}
GET  /v1/vector_stores/{vector_store_id}/file_batches/{batch_id}/files
GET  /v1/vector_stores/{vector_store_id}/files
GET  /v1/vector_stores/{vector_store_id}/files/{file_id}
GET  /v1/vector_stores/{vector_store_id}/files/{file_id}/content
DELETE /v1/vector_stores/{vector_store_id}/files/{file_id}
POST /v1/responses
POST /v1/responses/compact
POST /v1/responses/input_tokens
POST /v1/containers
POST /v1/containers/{container_id}/files
POST /v1/chatkit/sessions
POST /v1/chatkit/sessions/{session_id}/cancel
POST /v1/chatkit/threads
POST /v1/responses/{response_id}/cancel
POST /v1/completions
POST /v1/assistants
POST /v1/assistants/{assistant_id}
POST /v1/threads
POST /v1/threads/{thread_id}
POST /v1/threads/{thread_id}/messages
POST /v1/threads/{thread_id}/messages/{message_id}
POST /v1/threads/{thread_id}/runs
POST /v1/threads/{thread_id}/runs/{run_id}
POST /v1/threads/{thread_id}/runs/{run_id}/cancel
POST /v1/threads/{thread_id}/runs/{run_id}/submit_tool_outputs
POST /v1/threads/runs
POST /v1/chat/completions
POST /v1/chat/completions/{completion_id}
POST /v1/embeddings
POST /v1/images/generations
POST /v1/images/edits
POST /v1/images/variations
POST /v1/moderations
POST /v1/audio/speech
POST /v1/audio/transcriptions
POST /v1/audio/translations
GET  /v1/audio/voices
POST /v1/audio/voices
GET  /v1/audio/voice_consents
POST /v1/audio/voice_consents
GET  /v1/audio/voice_consents/{consent_id}
POST /v1/audio/voice_consents/{consent_id}
DELETE /v1/audio/voice_consents/{consent_id}
POST /v1/realtime/sessions
POST /v1/realtime/transcription_sessions
POST /v1/realtime/calls/{call_id}/accept
POST /v1/realtime/calls/{call_id}/hangup
POST /v1/realtime/calls/{call_id}/refer
POST /v1/realtime/calls/{call_id}/reject
POST /v1/files
POST /v1/uploads
POST /v1/uploads/{upload_id}/parts
POST /v1/uploads/{upload_id}/complete
POST /v1/uploads/{upload_id}/cancel
POST /v1/batches
POST /v1/batches/{batch_id}/cancel
POST /v1/videos
POST /v1/videos/{video_id}/remix
POST /v1/videos/edits
POST /v1/videos/extensions
/v1/organization/*
/v1/projects/{project_id}/*
GET  /v1/fine_tuning/jobs
POST /v1/fine_tuning/jobs
GET  /v1/fine_tuning/jobs/{fine_tuning_job_id}
POST /v1/fine_tuning/jobs/{fine_tuning_job_id}/cancel
GET  /v1/fine_tuning/jobs/{fine_tuning_job_id}/checkpoints
GET  /v1/fine_tuning/jobs/{fine_tuning_job_id}/events
POST /v1/fine_tuning/jobs/{fine_tuning_job_id}/pause
POST /v1/fine_tuning/jobs/{fine_tuning_job_id}/resume
GET  /v1/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions
POST /v1/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions
DELETE /v1/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions/{permission_id}
POST /v1/fine_tuning/alpha/graders/run
POST /v1/fine_tuning/alpha/graders/validate
POST /v1/evals
POST /v1/evals/{eval_id}
POST /v1/evals/{eval_id}/runs
POST /v1/evals/{eval_id}/runs/{run_id}
POST /v1/vector_stores
POST /v1/vector_stores/{vector_store_id}/file_batches
POST /v1/vector_stores/{vector_store_id}/file_batches/{batch_id}/cancel
POST /v1/vector_stores/{vector_store_id}/files
POST /v1/vector_stores/{vector_store_id}/items
POST /v1/vector_stores/{vector_store_id}/search
POST /v1/local/evals/text_expectation
```

Example:

```bash
curl -s http://127.0.0.1:8787/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{"input":"Reply exactly: proxy OAuth connected"}'
```

Existing OpenAI Python SDK clients can use the same local proxy by changing
`base_url` and using any non-empty local placeholder key:

```python
from openai import OpenAI

client = OpenAI(
    api_key="oauth-local-proxy",
    base_url="http://127.0.0.1:8787/v1",
)

response = client.responses.create(
    model="gpt-5.5",
    input="Reply exactly: SDK OAuth connected",
)
print(response.output_text)

for chunk in client.chat.completions.create(
    model="gpt-5.5",
    messages=[{"role": "user", "content": "Reply exactly: streaming works"}],
    stream=True,
):
    print(chunk.choices[0].delta.content or "", end="")
```

Local Assistants/Threads also work through the SDK beta surface against this
local proxy. They are local compatibility objects; hosted OpenAI Assistants
still require normal Platform API auth.

```python
assistant = client.beta.assistants.create(
    model="gpt-5.5",
    name="local-helper",
    instructions="Reply briefly.",
)
thread = client.beta.threads.create(
    messages=[{"role": "user", "content": "Reply exactly: local assistant ok"}],
)
run = client.beta.threads.runs.create(thread.id, assistant_id=assistant.id)
print(run.status)
```

## Run The Probes

Normal OAuth matrix:

```bash
PYTHONPATH=src python src/run_oauth_matrix.py
```

Official API surface audit:

```bash
python bridge.py audit
```

Run this once on a fresh clone before `classify`, `coverage`, `policy`, `guide`,
`check`, `migrate`, `boundaries`, and `quickstart`. It writes the gitignored
`reports/openai_surface_audit_latest.json` that those commands read.

If the current shell cannot reach the OpenAI OpenAPI source, `audit` reuses the
latest checked-in path list and writes a source warning into the report instead
of silently pretending the spec was refreshed.

The current OpenAI Developer Docs endpoint index check returned `172` paths
under `https://api.openai.com/v1`, matching the local audit count. That is
official docs parity evidence, not a live hosted-API smoke test; `/v1/videos`
still documents `OPENAI_API_KEY` examples and `/v1/organization/projects`
documents Admin API key auth.

Classify one OpenAI API path (requires `python bridge.py audit` first on a
fresh clone):

```bash
python bridge.py classify /v1/embeddings
python bridge.py classify /v1/assistants
```

Local proxy smoke:

```bash
python bridge.py smoke --include-images
```

Omit `--include-images` for a faster non-image proxy smoke.

OpenAI Python SDK proxy smoke:

```bash
python bridge.py sdk-smoke --include-images
```

Live launch gate:

```bash
python bridge.py live-check
python bridge.py live-check --include-images
bash reports/openai_bridge_launch_gate.sh
```

GitHub/clone-user publish gate:

```bash
python bridge.py publish-check
python bridge.py publish-check --strict
python bridge.py publish-api --dry-run
bash reports/openai_bridge_publish_gate.sh --push
python bridge.py finish --push
bash reports/openai_bridge_finish_gate.sh --push
```

Current full-goal readiness summary:

```bash
python bridge.py readiness
```

Full-goal verdict with requirement-by-requirement evidence:

```bash
python bridge.py verdict
python bridge.py verdict --strict
```

Use plain `verdict` for a report that exits successfully even when the answer is
not complete. Use `verdict --strict` in automation when incomplete must fail.

One-screen user status dashboard:

```bash
python bridge.py status
python bridge.py status --no-refresh-env
python bridge.py status --no-refresh-env --no-write
```

Most report-style commands now accept `--no-write` through `bridge.py` itself,
including `env`, `readiness`, `guide`, `config`, `coverage`, `policy`,
`boundaries`, `status`, `verdict`, `check`, `migrate`, `audit`,
`preflight`, `publish-check`, `live-check`, `doctor`, and the smoke commands. Use it when
you want current evidence without updating tracked `reports/*.md` files.

Machine-readable allow/deny/fallback route policy (needs the audit report; run
`python bridge.py audit` first on a fresh clone):

```bash
python bridge.py policy
```

User-facing compatibility guide (needs the audit report; run
`python bridge.py audit` first on a fresh clone):

```bash
python bridge.py guide
python bridge.py guide --category api_key_or_admin_key_required --limit 20
```

Product-group coverage map (needs the audit report; run
`python bridge.py audit` first on a fresh clone):

```bash
python bridge.py coverage
python bridge.py coverage --group realtime
```

Safe playbook for remaining Platform/Admin boundaries (needs the audit report;
run `python bridge.py audit` first on a fresh clone):

```bash
python bridge.py boundaries
```

Optional Platform/Admin credential fallback status:

```bash
python bridge.py fallback
python bridge.py fallback /v1/videos/edits /v1/organization/projects
```

The fallback is disabled by default. If you explicitly set
`OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1`, the local proxy can forward official
OpenAI API requests using `OPENAI_API_KEY`, `OPENAI_ACCESS_TOKEN`, or
`OPENAI_ADMIN_KEY` when a route is still a boundary or when you choose hosted
behavior over a local compatibility handler. `OPENAI_ACCESS_TOKEN` is for
official OpenAI workload-identity-style bearer tokens, not a ChatGPT/Codex
OAuth session token. This is hybrid routing, not an OAuth bypass, and reports
only show whether credentials are present, never the credential values. The
default fallback mode is `boundary`, so local compatibility handlers still run
locally. Set `OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=prefer` or send
`X-OAuth-Compat-Prefer-Platform: 1` when you intentionally want hosted OpenAI
API behavior to take precedence over local compatibility handlers. The SDK
placeholder value `oauth-local-proxy` is ignored as a Platform credential.

Generate SDK, curl, and environment configuration for local bridge clients:

```bash
python bridge.py config
python bridge.py config --base-url http://127.0.0.1:8787/v1
python bridge.py quickstart
```

`config` also writes `reports/openai_bridge.env.example` and
`reports/openai_bridge_ci_gate.sh` so app setup and CI checks use the same
bridge base URL, placeholder SDK key, preflight, verdict, and boundary gate.
It also writes `reports/openai_bridge_launch_gate.sh`, which runs
`python bridge.py live-check` for launch-ready evidence in a normal local shell.
For publishing, it writes `reports/openai_bridge_publish_gate.sh`; run it with
`--push` from a normal networked shell to run no-write preflight, push the
current branch, refresh the local `origin/<branch>` ref, and re-run
`publish-check --no-write --strict`.
If `git push` fails but `GITHUB_TOKEN` or `GH_TOKEN` is available, the publish
gate falls back to `python bridge.py publish-api --branch <branch>`, which
creates the GitHub tree/commit/ref through the Git data API. Use
`python bridge.py publish-api --dry-run` first to check the target repo, branch,
and changed paths without writing. In a no-network shell, `--dry-run` falls back
to the local `origin/<branch>` tracking ref so users can still inspect the
publish plan before moving to a networked shell. In a networked token shell,
`publish-api` reads both the branch ref and base tree from GitHub before writing,
so it does not depend on a freshly fetched local `origin/<branch>`.
The latest plan is written to `reports/github_api_publish_plan_latest.md/json`
unless `--no-write` is passed.
It also writes `reports/openai_bridge_finish_gate.sh`; run it with `--push`
when you want publish and live-launch gates in one end-to-end command.
`quickstart` additionally writes `reports/quickstart_latest.md/json` and
regenerates the route policy and full-goal audit so users can start from one
bundle instead of combining several commands by hand. It reads the surface audit
report, so on a fresh clone run `python bridge.py audit` first or it fails with a
missing-report error.
The generated env example also lists optional Realtime model overrides such as
`OAUTH_BRIDGE_REALTIME_MODEL=gpt-realtime-2` and
`OAUTH_BRIDGE_REALTIME_TRANSCRIPTION_MODEL=gpt-realtime-whisper` for apps that
want to follow the current Realtime guide while preserving the last local matrix
default unless explicitly changed.

Check a path list or scan your app source (needs the audit report; run
`python bridge.py audit` first on a fresh clone):

```bash
python bridge.py check /v1/embeddings /v1/assistants /v1/videos/edits
python bridge.py check path/to/your/app --fail-on-boundary
```

`check` scans OpenAI REST URLs, quoted `/v1/...` path literals, and OpenAI SDK
method calls such as `client.responses.create`, `openai.responses.create`,
`client.organization.projects.list`, `openai.vectorStores.create`, and aliases
created with `openai_client = OpenAI()` or `const ai = new OpenAI()`. The
preflight verifies SDK method coverage against all `172` currently documented
OpenAI API paths, so new official paths should break the gate until the scanner
knows how to classify them.

Generate a paste-ready app migration plan (needs the audit report; run
`python bridge.py audit` first on a fresh clone):

```bash
python bridge.py migrate path/to/your/app
python bridge.py migrate path/to/your/app --fail-on-boundary
```

`migrate` uses the same scanner, but writes `reports/migration_plan_latest.md`
with the local `OPENAI_BASE_URL`, placeholder SDK key, start command, CI gate,
ready routes, and blocked/API-key-boundary routes in one place.

Current local environment probe:

```bash
python bridge.py env
```

No-network, no-socket local router smoke:

```bash
python bridge.py offline-smoke
```

Release preflight before commit/publish:

```bash
python bridge.py preflight
python bridge.py preflight --no-write
```

Preflight includes the current environment probe, no-network `offline-smoke`,
route manifest/docs consistency, surface audit regeneration, readiness report
generation, compatibility guide and coverage-map generation, usage
compatibility checks, boundary playbook generation, compile checks, client configuration, quickstart bundle, platform fallback
status, SDK usage-scanner coverage, status and doctor report generation,
representative path classification, whitespace checks, required report
presence, and a local secret scan.
It does not require live network or localhost bind success; use
`python bridge.py live-check` for the launch-ready evidence gate in a normal
local shell. Use `preflight --no-write` after committing when you want the
publish/finish gate behavior without refreshing timestamped reports.

## Troubleshooting

If `python bridge.py info` shows `model_discovery_error`, the bridge found a
local OAuth token but could not reach the Codex backend from the current
environment. Local metadata routes can still initialize with the default model,
but text, image, embedding, audio, file upload, and other network-backed methods
need network access.
When `python bridge.py env` reports `dns_or_network_blocked=True`, the current
shell cannot resolve the external hosts needed for launch proof. Move to a
normal shell that can resolve `chatgpt.com`, `github.com`, and `api.openai.com`.

If `python bridge.py smoke` or `python bridge.py sdk-smoke` prints
`Cannot start local proxy ... localhost socket binding`, the current sandbox or
host policy is blocking local port binding. Run the same command in a normal
local shell, or start the proxy manually with:

```bash
python bridge.py serve --port 8787
```
When `python bridge.py env` reports `localhost_socket_denied=True`, changing
ports will not fix this sandbox; the shell is not allowed to bind sockets.

`python bridge.py offline-smoke` still works in those restricted environments.
It does not prove live OpenAI/ChatGPT network access; it only checks that the
local compatibility router logic still returns coherent OpenAI-shaped objects.
It also checks templated official paths such as `/v1/videos/{id}/remix`, which
now route to local video storyboard/remix metadata instead of hosted MP4
rendering.
`python bridge.py env` writes `reports/environment_latest.md` with the current
token-source, Codex model-discovery, and localhost-bind evidence.

Deeper ChatGPT/Codex backend sweep:

```bash
PYTHONPATH=src python src/run_deep_oauth_research.py
```

The runners write sanitized reports under `reports/` and generated proof artifacts under `artifacts/`. JSON reports and generated artifacts are ignored by git.

Latest checked-in summaries:

- [`RESULTS_SUMMARY.md`](RESULTS_SUMMARY.md)
- [`USABLE_OAUTH_METHODS.md`](USABLE_OAUTH_METHODS.md)
- [`DEEP_OAUTH_RESEARCH.md`](DEEP_OAUTH_RESEARCH.md)
- [`LEGAL_OAUTH_WORKAROUNDS.md`](LEGAL_OAUTH_WORKAROUNDS.md)
- [`OFFICIAL_BOUNDARY.md`](OFFICIAL_BOUNDARY.md)
- [`reports/openai_surface_audit_latest.md`](reports/openai_surface_audit_latest.md)
- [`reports/compatibility_guide_latest.md`](reports/compatibility_guide_latest.md)
- [`reports/coverage_map_latest.md`](reports/coverage_map_latest.md)
- [`reports/openai_bridge_route_policy.md`](reports/openai_bridge_route_policy.md)
- [`reports/openai_bridge_route_policy.csv`](reports/openai_bridge_route_policy.csv)
- [`reports/boundary_playbook_latest.md`](reports/boundary_playbook_latest.md)
- [`reports/client_config_latest.md`](reports/client_config_latest.md)
- [`reports/quickstart_latest.md`](reports/quickstart_latest.md)
- [`reports/openai_bridge.env.example`](reports/openai_bridge.env.example)
- [`reports/openai_bridge_ci_gate.sh`](reports/openai_bridge_ci_gate.sh)
- [`reports/platform_fallback_latest.md`](reports/platform_fallback_latest.md)
- [`reports/goal_audit_latest.md`](reports/goal_audit_latest.md)
- [`reports/status_latest.md`](reports/status_latest.md)
- [`reports/usage_check_latest.md`](reports/usage_check_latest.md)
- [`reports/migration_plan_latest.md`](reports/migration_plan_latest.md)
- [`reports/doctor_latest.md`](reports/doctor_latest.md)
- [`reports/readiness_latest.md`](reports/readiness_latest.md)
- [`reports/environment_latest.md`](reports/environment_latest.md)
- [`reports/proxy_smoke_latest.md`](reports/proxy_smoke_latest.md)
- [`reports/openai_sdk_proxy_smoke_latest.md`](reports/openai_sdk_proxy_smoke_latest.md)

## Secret Handling

The code reads local OAuth files:

```text
~/.codex/auth.json
~/.hermes/auth.json
```

It does not commit, print, or store raw access tokens, refresh tokens, Authorization headers, API keys, signed upload URLs, or raw auth files.

Before publishing your own fork, run:

```bash
python bridge.py preflight
python bridge.py preflight --no-write
```

Docs may mention token field names as labels, but actual secret values should
never appear. The preflight skips ignored generated data and checks source/docs
for obvious Bearer tokens, OpenAI API keys, Admin keys, JSON token values, and
signed URL leaks.

## Project Layout

```text
bridge.py                           User-facing setup/info/serve/smoke/audit CLI
src/codex_oauth.py                 OAuth source selection and Codex headers
setup_oauth.py                     One-command OAuth setup checker
src/github_api_publish.py          GitHub API fallback publisher for clean local HEAD
src/openai_oauth_access.py          Main OAuth-only wrapper
src/oauth_feature_router.py         OpenAI-like compatibility layer
src/oauth_openai_compat_server.py   Local /v1 compatibility server
src/run_oauth_matrix.py             Broad OAuth capability matrix
src/audit_openai_surface.py         Official API surface coverage audit
src/classify_openai_path.py         Query one API path against the latest audit
src/generate_compatibility_guide.py User-facing route decision guide
src/generate_coverage_map.py        Product-group direct/local/API-key coverage map
src/generate_route_policy.py        Machine-readable allow/deny/fallback route policy
src/generate_boundary_playbook.py   Safe-mode and fallback playbook for remaining boundaries
src/generate_client_config.py       SDK/curl/env configuration for local clients
src/generate_quickstart.py          First-run env, CI gate, route policy, and verdict bundle
src/platform_fallback_status.py     Optional Platform/Admin fallback status without printing keys
src/goal_audit_report.py            Full-goal verdict and user-facing go/no-go audit
src/status_report.py                One-screen readiness/config/next-action status
src/check_openai_usage.py           Scan paths/files for direct/local/API-key route decisions
src/generate_migration_plan.py      App migration plan with base URL, CI gate, and blockers
src/doctor_report.py                User-facing package, environment, and full-goal diagnostics
src/run_proxy_smoke.py              One-command local /v1 proxy smoke test
src/run_openai_sdk_proxy_smoke.py   OpenAI Python SDK compatibility smoke
src/run_router_offline_smoke.py     No-network/no-socket local router smoke
src/verify_route_manifest.py        Capability, route output, and docs consistency check
src/verify_summary_counts.py        Summary docs and latest report count consistency check
src/verify_usage_scanner.py         SDK scanner coverage against the official API surface
src/readiness_report.py             Full-goal readiness summary from current evidence
src/environment_probe.py            Current token, network, and localhost bind probe
src/release_preflight.py            Env, offline smoke, route, audit, guide, coverage, config, fallback, goal audit, status, usage/migration checks, doctor, readiness, compile, report, whitespace, and secret preflight
src/live_launch_check.py            Live launch gate: env, HTTP proxy smoke, SDK smoke, readiness, strict doctor
src/run_deep_oauth_research.py      ChatGPT/Codex backend probe runner
```

## Why This Exists

OpenAI's public Platform API is documented around API-key authentication. Codex and ChatGPT also use OAuth sessions for their own product surfaces. This repo keeps those two worlds separate: it tests what a real Codex/ChatGPT OAuth session can do, documents what is blocked, and gives local wrappers for the usable parts.
