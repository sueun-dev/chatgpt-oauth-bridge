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
- Realtime transcription sessions
- Realtime WebRTC call setup with a real SDP offer
- ChatGPT/Codex backend file upload
- ChatGPT plugin and connector catalog reads
- Codex task/environment metadata reads
- Codex Apps MCP discovery and read-only public GitHub search
- Local files, vector stores, and eval compatibility layers
- Local `/v1/responses`, `/v1/chat/completions`, `/v1/embeddings`, and `/v1/images/generations` proxy

Known boundaries:

- OpenAI Platform `/v1/responses`, `/v1/chat/completions`, `/v1/images/...`, `/v1/audio/speech`, `/v1/files`, hosted vector stores, fine-tuning, evals, videos, containers, Assistants, ChatKit sessions, Admin, and Usage are still API-key/Admin-key surfaces unless a tested OAuth route is listed in this repo.
- Some features are handled honestly through local compatibility layers, for example local vector stores plus OAuth embeddings.

## Install

```bash
git clone https://github.com/sueun-dev/chatgpt-oauth-bridge.git
cd chatgpt-oauth-bridge

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Connect OAuth In One Check

Run the setup checker first:

```bash
python setup_oauth.py
```

If dependencies are missing, it prints the exact `venv` and `pip install` commands. If OAuth is missing, it prints the exact login commands. If OAuth is ready, it prints the selected token source, visible model count, chosen text/image models, and a tiny text smoke result.

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
python setup_oauth.py
PYTHONPATH=src python src/openai_oauth_access.py
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
PYTHONPATH=src python src/oauth_openai_compat_server.py --port 8787
```

Point a local app to:

```text
http://127.0.0.1:8787/v1
```

Supported routes:

```text
GET  /health
POST /v1/responses
POST /v1/chat/completions
POST /v1/embeddings
POST /v1/images/generations
```

Example:

```bash
curl -s http://127.0.0.1:8787/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{"input":"Reply exactly: proxy OAuth connected"}'
```

## Run The Probes

Normal OAuth matrix:

```bash
PYTHONPATH=src python src/run_oauth_matrix.py
```

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

## Secret Handling

The code reads local OAuth files:

```text
~/.codex/auth.json
~/.hermes/auth.json
```

It does not commit, print, or store raw access tokens, refresh tokens, Authorization headers, API keys, signed upload URLs, or raw auth files.

Before publishing your own fork, run:

```bash
rg -n 'Bearer|access_token|refresh_token|sk-[A-Za-z0-9]|ek_[A-Za-z0-9]|download_url\?' .
```

Docs may mention those words as labels, but actual secret values should never appear.

## Project Layout

```text
src/codex_oauth.py                 OAuth source selection and Codex headers
setup_oauth.py                     One-command OAuth setup checker
src/openai_oauth_access.py          Main OAuth-only wrapper
src/oauth_feature_router.py         OpenAI-like compatibility layer
src/oauth_openai_compat_server.py   Local /v1 compatibility server
src/run_oauth_matrix.py             Broad OAuth capability matrix
src/run_deep_oauth_research.py      ChatGPT/Codex backend probe runner
```

## Why This Exists

OpenAI's public Platform API is documented around API-key authentication. Codex and ChatGPT also use OAuth sessions for their own product surfaces. This repo keeps those two worlds separate: it tests what a real Codex/ChatGPT OAuth session can do, documents what is blocked, and gives local wrappers for the usable parts.
