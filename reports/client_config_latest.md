# OAuth Bridge Client Config

- Generated: `2026-06-01T17:49:54Z`
- Base URL: `http://127.0.0.1:8787/v1`
- Placeholder API key: `oauth-local-proxy`
- Goal complete: `False`
- Bottom line: Not complete: every documented path is mapped to direct OAuth or explicit local compatibility, but only 5 paths are direct hosted OAuth and this environment cannot prove live Codex network access and localhost SDK smoke.
- Env example: `reports/openai_bridge.env.example`
- CI gate: `reports/openai_bridge_ci_gate.sh`
- Launch gate: `reports/openai_bridge_launch_gate.sh`
- Publish gate: `reports/openai_bridge_publish_gate.sh`
- Finish gate: `reports/openai_bridge_finish_gate.sh`

## Category Counts

| Category | Paths |
|---|---:|
| `direct_official_oauth_verified` | 5 |
| `local_compat_or_chatgpt_backend_bridge` | 167 |

## Start The Proxy

```bash
python bridge.py serve --host 127.0.0.1 --port 8787
```

## Environment Variables

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8787/v1
export OPENAI_API_KEY=oauth-local-proxy
```

## Optional Platform Fallback

```bash
export OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1 OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=boundary OPENAI_API_KEY=sk-...
# exact hosted API behavior before local compatibility handlers:
export OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1 OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=prefer OPENAI_API_KEY=sk-...
```

## Python SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="oauth-local-proxy",
    base_url="http://127.0.0.1:8787/v1",
)

response = client.responses.create(
    model="gpt-5.5",
    input="Reply exactly: bridge ready",
)
print(response.output_text)
```

## JavaScript SDK

```js
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "oauth-local-proxy",
  baseURL: "http://127.0.0.1:8787/v1",
});

const response = await client.responses.create({
  model: "gpt-5.5",
  input: "Reply exactly: bridge ready",
});
console.log(response.output_text);
```

## cURL

```bash
curl -s http://127.0.0.1:8787/health
curl -s 'http://127.0.0.1:8787/v1/oauth-classify?path=/v1/embeddings'
curl -s http://127.0.0.1:8787/v1/responses -H 'Content-Type: application/json' -H 'Authorization: Bearer oauth-local-proxy' -d '{"model":"gpt-5.5","input":"Reply exactly: bridge ready"}'
```

## Metadata Endpoints

| Name | URL |
|---|---|
| `health` | `http://127.0.0.1:8787/health` |
| `capabilities` | `http://127.0.0.1:8787/v1/oauth-capabilities` |
| `readiness` | `http://127.0.0.1:8787/v1/oauth-readiness` |
| `compatibility_guide` | `http://127.0.0.1:8787/v1/oauth-compatibility-guide` |
| `quickstart` | `http://127.0.0.1:8787/v1/oauth-quickstart` |
| `coverage_map` | `http://127.0.0.1:8787/v1/oauth-coverage-map` |
| `route_policy` | `http://127.0.0.1:8787/v1/oauth-route-policy` |
| `status` | `http://127.0.0.1:8787/v1/oauth-status` |
| `goal_audit` | `http://127.0.0.1:8787/v1/oauth-goal-audit` |
| `classify_embeddings` | `http://127.0.0.1:8787/v1/oauth-classify?path=/v1/embeddings` |
| `client_config` | `http://127.0.0.1:8787/v1/oauth-client-config` |

## Warnings

- This base_url points to the local bridge, not hosted https://api.openai.com/v1.
- Use bridge.py check before migrating an app; any route reported as an API/Admin-key boundary must stay disabled or use official Platform credentials.
- Use bridge.py migrate for a paste-ready migration plan with base_url, SDK key, CI gate, and blocked route list.
- Use bridge.py coverage for a product-group view of direct OAuth, local bridge, and Platform-credential boundaries.
- The placeholder API key is only for SDK clients that require a non-empty key; the local proxy uses the local ChatGPT/Codex OAuth session.
- Run bridge.py live-check from a normal local shell before making launch-ready claims.
- Run bridge.py publish-check before claiming GitHub or clone users have the latest bridge.
- Use bridge.py publish-api --dry-run to validate the GitHub API publish fallback before using it with GITHUB_TOKEN or GH_TOKEN.
- Use reports/openai_bridge_publish_gate.sh --push from a normal networked shell to run no-write preflight, push the current branch, refresh origin, and re-check publish state.
- Use reports/openai_bridge_finish_gate.sh --push from a normal networked shell to run publish and live launch gates in order.
- Run bridge.py readiness before claiming the whole OpenAI API surface is available through OAuth.
- Set OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1 plus OPENAI_API_KEY, OPENAI_ACCESS_TOKEN, or OPENAI_ADMIN_KEY only when you intentionally want the local proxy to forward requests to the official Platform API.
- Default fallback mode is boundary. Set OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=prefer only when you want hosted OpenAI API behavior to take precedence over local compatibility handlers.
