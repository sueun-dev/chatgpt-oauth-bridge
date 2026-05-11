# GitHub Repo Setup

Selected repository name:

```text
chatgpt-oauth-bridge
```

Short description:

```text
Use ChatGPT/Codex OAuth sessions for text, images, Realtime audio, embeddings, files, and local OpenAI-compatible routes. No API keys.
```

Suggested topics:

```text
chatgpt
codex
oauth
openai
realtime
embeddings
image-generation
mcp
compatibility-layer
api-research
```

## Create The Repo

```bash
gh repo create chatgpt-oauth-bridge \
  --public \
  --description "Use ChatGPT/Codex OAuth sessions for text, images, Realtime audio, embeddings, files, and local OpenAI-compatible routes. No API keys."
```

## Connect OAuth

Use Codex CLI:

```bash
codex login --device-auth
codex login status
```

Expected local token file:

```text
~/.codex/auth.json
```

Or use Hermes:

```bash
hermes login --provider openai-codex
hermes auth status openai-codex
```

Expected local token file:

```text
~/.hermes/auth.json
```

This project reads those local OAuth sessions in memory. It does not commit or print token values.

## Smoke Test

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python setup_oauth.py
PYTHONPATH=src python src/openai_oauth_access.py
```

## Full Test Run

```bash
PYTHONPATH=src python src/run_oauth_matrix.py
PYTHONPATH=src python src/run_deep_oauth_research.py
```

## Local OpenAI-Compatible Proxy

```bash
PYTHONPATH=src python src/oauth_openai_compat_server.py --port 8787
```

Use this as the base URL in a local app:

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

## Public Repo Safety Checklist

Before pushing:

```bash
rg -n 'Bearer|access_token|refresh_token|sk-[A-Za-z0-9]|ek_[A-Za-z0-9]|download_url\?' .
```

Never commit:

```text
~/.codex/auth.json
~/.hermes/auth.json
.env
data/
artifacts/*.png
artifacts/*.pcm16
reports/*.json
```

Use this boundary in public docs:

```text
This is not an official OpenAI SDK and does not bypass authorization. It uses OAuth sessions from the user's own Codex/ChatGPT login and records which routes accept that token. Blocked Platform resources are documented as blocked or handled through local compatibility layers.
```
