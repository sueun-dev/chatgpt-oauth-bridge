# OAuth Usage Examples

이 문서는 지금 이 폴더에서 실제로 만든 OAuth-only 래퍼를 어떻게 쓰는지에 대한 예시다. 전제는 하나다: `OPENAI_API_KEY` 없이 Codex/ChatGPT OAuth 토큰만 쓴다.

먼저 터미널에서 이걸 잡고 시작한다.

```bash
cd chatgpt-oauth-bridge
PY=python
```

토큰은 출력하지 않는다. Hermes 토큰이 만료되어 있으면 `src/codex_oauth.py`가 현재 Codex CLI OAuth 토큰으로 fallback한다.

연결 상태부터 보고 싶으면:

```bash
$PY bridge.py setup
```

## 0a. Hybrid Platform Fallback

무엇인가: ChatGPT/Codex OAuth로 안 열리는 official Platform route는 기본적으로
structured boundary error를 낸다. 같은 local proxy base URL을 유지하면서
official Platform credential을 명시적으로 섞고 싶을 때만 fallback을 켠다.

```bash
export OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1
export OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=boundary
export OPENAI_API_KEY=sk-...

$PY bridge.py fallback /v1/responses /v1/fine_tuning/jobs/ftjob_123/cancel
```

`boundary` mode에서는 blocked route만 official OpenAI API로 forward되고,
local compatibility route는 계속 로컬 처리된다. 정확한 hosted API 동작이
local compatibility보다 먼저 필요하면 아래처럼 opt-in 한다.

```bash
export OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=prefer
# or per request:
curl -s http://127.0.0.1:8787/v1/responses \
  -H 'Content-Type: application/json' \
  -H 'X-OAuth-Compat-Prefer-Platform: 1' \
  -d '{"model":"gpt-5.5","input":"Reply exactly: hosted first"}'
```

## 1. Text / Responses 대체

무엇인가: 공식 `/v1/responses`가 Codex OAuth로 직접 열리는 것은 아니지만, 같은 "텍스트 응답 생성" 기능은 Codex OAuth `responses` surface로 처리한다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
text = oauth.codex_text("Reply exactly: text oauth ok")
print(text)
PY
```

OpenAI-style wrapper로 쓰고 싶으면:

```bash
PYTHONPATH=src $PY - <<'PY'
from oauth_feature_router import OAuthFeatureRouter

router = OAuthFeatureRouter()
res = router.responses_create("Reply exactly: response compat ok")
print(res["route"])
print(res["output_text"])
PY
```

## 2. Chat Completions 대체

무엇인가: `/v1/chat/completions` endpoint 자체가 OAuth로 열리는 것은 아니지만, `messages` 배열을 Codex text prompt로 변환해서 assistant 응답을 만든다.

```bash
PYTHONPATH=src $PY - <<'PY'
from oauth_feature_router import OAuthFeatureRouter

router = OAuthFeatureRouter()
res = router.chat_completions_create([
    {"role": "system", "content": "Answer briefly."},
    {"role": "user", "content": "Reply exactly: chat oauth ok"},
])
print(res["route"])
print(res["message"]["content"])
PY
```

## 2a. Legacy Completions 대체

무엇인가: hosted `/v1/completions`는 Platform credential 경계지만, 오래된 앱 호환을 위해 local proxy와 router가 `prompt`를 Codex text completion으로 바꿔준다.

```bash
PYTHONPATH=src $PY - <<'PY'
from oauth_feature_router import OAuthFeatureRouter

router = OAuthFeatureRouter()
res = router.completions_create("Reply exactly: legacy completion compat ok")
print(res["route"])
print(res["text"])
PY
```

## 2b. Responses Input Tokens 대체

무엇인가: hosted `/v1/responses/input_tokens`는 Platform credential 경계지만, 로컬 앱의 길이/비용 사전 체크용으로 명시적인 approximate estimate를 제공한다. 공식 tokenizer 값이 아니라 `estimated=True`인 local estimate다.

```bash
PYTHONPATH=src $PY - <<'PY'
from oauth_feature_router import OAuthFeatureRouter

router = OAuthFeatureRouter()
res = router.responses_input_tokens_estimate("Count this local prompt.")
print(res["route"])
print(res["input_tokens"])
print(res["estimated"])
PY
```

## 2c. Responses Compact 대체

무엇인가: hosted `/v1/responses/compact`는 Platform credential 경계지만, 로컬 앱에서 긴 입력을 줄여 저장하려는 경우 `response.compaction` 모양의 local object를 돌려준다. `encrypted_content`는 hosted OpenAI 암호문이 아니라 로컬 호환용 base64 payload다.

```bash
PYTHONPATH=src $PY - <<'PY'
from oauth_feature_router import OAuthFeatureRouter

router = OAuthFeatureRouter()
res = router.responses_compact("Compact this local prompt and preserve compact-ok.")
print(res["route"])
print(res["object"])
print(bool(res["encrypted_content"]))
PY
```

## 3. Vision Input

무엇인가: 이미지 파일을 data URL로 넣고 Codex OAuth text model에 vision input을 보낸다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
answer = oauth.codex_vision(
    "artifacts/vision_probe_red_square.png",
    "What color is the square? Answer in one word.",
)
print(answer)
PY
```

## 4. Image Generation

무엇인가: 공식 `/v1/images/generations` 대신 Codex OAuth `image_generation` tool을 호출한다. 결과는 로컬 PNG로 저장된다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
path = oauth.codex_generate_image(
    "A clean technical diagram of OAuth tokens flowing through a local gateway, no text",
    "artifacts/example_image.png",
)
print(path)
PY
```

OpenAI-style wrapper:

```bash
PYTHONPATH=src $PY - <<'PY'
from oauth_feature_router import OAuthFeatureRouter

router = OAuthFeatureRouter()
res = router.images_generate(
    "A small blue cube on a white background, product-render style",
    "artifacts/example_router_image.png",
)
print(res["route"])
print(res["path"])
PY
```

## 5. Drawing Generation

무엇인가: 이미지 생성과 같은 OAuth image_generation route다. prompt를 그림/스케치 쪽으로 주면 된다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
path = oauth.codex_generate_image(
    "A simple black ink line drawing of a laptop connected to a cloud, white background",
    "artifacts/example_drawing.png",
)
print(path)
PY
```

## 6. Speech-to-Text

무엇인가: 이건 대체가 아니라 공식 `POST /v1/audio/transcriptions`가 Codex OAuth token으로 실제 통과했다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.official_transcribe_audio("artifacts/tiny_silence.wav")
print(res.get("_http_status"))
print(res.get("text", ""))
PY
```

Router wrapper:

```bash
PYTHONPATH=src $PY - <<'PY'
from oauth_feature_router import OAuthFeatureRouter

router = OAuthFeatureRouter()
res = router.audio_transcriptions_create("artifacts/tiny_silence.wav")
print(res.get("route"))
print(res.get("text", ""))
PY
```

## 7. Text-to-Speech 대체

무엇인가: 공식 `/v1/audio/speech`는 막혔다. 대신 Realtime WebSocket audio response로 PCM16 음성을 만든다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
path = oauth.realtime_say_to_pcm("oauth voice ok", "artifacts/example_voice.pcm16")
print(path)
print(path.stat().st_size)
PY
```

Router wrapper:

```bash
PYTHONPATH=src $PY - <<'PY'
from oauth_feature_router import OAuthFeatureRouter

router = OAuthFeatureRouter()
res = router.audio_speech_create("oauth router voice ok", "artifacts/example_router_voice.pcm16")
print(res["route"])
print(res["format"])
print(res["bytes"])
PY
```

## 8. Embeddings

무엇인가: 이건 대체가 아니라 공식 `POST /v1/embeddings`가 Codex OAuth token으로 실제 통과했다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.official_embedding("OAuth embeddings example")
vec = res["data"][0]["embedding"]
print(res.get("_http_status"))
print(len(vec))
print(vec[:3])
PY
```

Router wrapper:

```bash
PYTHONPATH=src $PY - <<'PY'
from oauth_feature_router import OAuthFeatureRouter

router = OAuthFeatureRouter()
res = router.embeddings_create("OAuth router embedding example")
print(res["route"])
print(len(res["data"][0]["embedding"]))
PY
```

## 9. Realtime Client Secret

무엇인가: 공식 `POST /v1/realtime/client_secrets`가 Codex OAuth token으로 통과했다. client secret 값은 민감하니 출력하지 말고 존재 여부만 본다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
secret = oauth.realtime_client_secret()
print("client_secret_present", bool(secret))
PY
```

## 10. Realtime Transcription Session

무엇인가: Realtime transcription session도 OAuth로 만들 수 있다. STT streaming UI를 만들 때 이걸 쓴다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.realtime_transcription_session()
print(res.get("_http_status"))
print(res.get("type"))
print("client_secret_present", bool(res.get("value") or res.get("client_secret")))
PY
```

Local proxy alias for SDKs/apps that still call the older session routes:

```bash
curl -sS http://127.0.0.1:8787/v1/realtime/sessions \
  -H 'Authorization: Bearer oauth-local-proxy' \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-realtime"}' | jq '{object, oauth_compat_route, requested_route, upstream_route, has_secret:(.client_secret.value != null)}'

curl -sS http://127.0.0.1:8787/v1/realtime/transcription_sessions \
  -H 'Authorization: Bearer oauth-local-proxy' \
  -H 'Content-Type: application/json' \
  -d '{}' | jq '{object, oauth_compat_route, requested_route, upstream_route, has_secret:(.client_secret.value != null)}'
```

## 11. Realtime WebRTC Call

무엇인가: `POST /v1/realtime/calls`는 OAuth 인증 경계는 넘는다. 실제 앱에서는 브라우저의 `RTCPeerConnection.createOffer()`로 만든 SDP offer를 넣어야 한다. 가짜 SDP 문자열로는 안 된다.

```bash
PYTHONPATH=src $PY - <<'PY'
from pathlib import Path
from openai_oauth_access import OpenAIOAuthAccess

offer_sdp = Path("offer.sdp").read_text()
oauth = OpenAIOAuthAccess()
res = oauth.realtime_webrtc_call_offer(
    offer_sdp,
    instructions="You are on a short OAuth-only voice call.",
)
print(res.get("_http_status"))
print(res.get("content_type"))
print((res.get("answer_sdp") or res.get("_error_prefix") or "")[:120])
PY
```

## 12. Realtime Translation Client Secret

무엇인가: `POST /v1/realtime/translations/client_secrets`도 Codex OAuth token으로 통과했다. 값은 민감하니 존재 여부만 확인한다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.realtime_translation_client_secret(language="es")
print(res.get("_http_status"))
print((res.get("session") or {}).get("type"))
print("client_secret_present", bool(res.get("value")))
PY
```

## 13. ChatGPT/Codex Backend File Upload

무엇인가: OpenAI Platform `/v1/files`가 아니라 ChatGPT backend `/backend-api/files` flow다. Codex Apps MCP file parameter 쪽에서 쓰는 실제 OAuth file upload다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.chatgpt_upload_file("artifacts/codex_backend_upload_probe.txt")
print(res["route"])
print(res["id"])
print(res["uri"])
print(res["download_url_present"])
PY
```

Router wrapper는 로컬 metadata도 같이 남긴다.

```bash
PYTHONPATH=src $PY - <<'PY'
from oauth_feature_router import OAuthFeatureRouter

router = OAuthFeatureRouter()
res = router.files_create("artifacts/codex_backend_upload_probe.txt", purpose="assistants")
print(res["route"])
print(res["id"])
print(res["local_metadata_path"])
print(router.files_list()["data"][-1]["filename"])
PY
```

## 14. Local Vector Store / RAG 대체

무엇인가: OpenAI-hosted vector store는 OAuth로 직접 생성되지 않는다. 대신 로컬 JSON vector store + OAuth embeddings로 RAG 검색을 처리한다.

```bash
PYTHONPATH=src $PY - <<'PY'
from oauth_feature_router import OAuthFeatureRouter

router = OAuthFeatureRouter()
store = router.vector_stores_create(name="oauth-example-rag")
router.vector_stores_add_text(
    store["id"],
    "Codex OAuth can generate text, images, audio, embeddings, and upload files through ChatGPT backend routes.",
    metadata={"source": "example"},
)
res = router.vector_stores_search(store["id"], "what can OAuth do?", limit=1)
print(store["id"])
print(res["route"])
print(res["data"][0]["score"])
print(res["data"][0]["text"])
PY
```

## 15. Local Eval 대체

무엇인가: OpenAI-hosted eval 리소스 대신, 로컬에서 prompt를 실행하고 기대 substring이 있는지 검사한다.

```bash
PYTHONPATH=src $PY - <<'PY'
from oauth_feature_router import OAuthFeatureRouter

router = OAuthFeatureRouter()
res = router.eval_text_expectation(
    "Reply exactly: eval oauth ok",
    "eval oauth ok",
)
print(res["route"])
print(res["passed"])
print(res["output_text"])
PY
```

## 15a. Fine-tuning Grader Preflight

무엇인가: hosted fine-tuning job은 여전히 Platform credential 경계다. 다만
`string_check`와 `multi` grader는 OpenAI grader 문서의 템플릿 규칙에 맞춰
로컬에서 미리 validate/run 할 수 있다.

```bash
PYTHONPATH=src $PY - <<'PY'
from oauth_feature_router import OAuthFeatureRouter

router = OAuthFeatureRouter()
grader = {
    "type": "string_check",
    "name": "exact_label",
    "input": "{{ sample.output_text }}",
    "reference": "{{ item.label }}",
    "operation": "eq",
}

print(router.fine_tuning_graders_validate(grader)["valid"])
res = router.fine_tuning_graders_run(
    grader,
    model_sample="approved",
    item={"label": "approved"},
)
print(res["route"])
print(res["reward"])
PY
```

## 16. Codex Apps MCP Tools Inventory

무엇인가: `chatgpt.com/backend-api/codex/apps` 쪽 MCP initialize/tools list flow다. 여기서는 GitHub/Gmail 같은 Codex Apps tool 목록이 OAuth로 보인다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.chatgpt_apps_tools_list()
tools = res.get("tools", [])
print(res.get("_http_status"))
print(len(tools))
print([t.get("name") for t in tools[:5]])
PY
```

## 17. Codex Apps GitHub Public Search

무엇인가: Codex Apps MCP tool call로 GitHub repository search를 호출한다. 이건 OpenAI Platform API가 아니라 ChatGPT/Codex Apps OAuth surface다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.chatgpt_github_search_repositories("codex", org="openai", per_page=3)
print(res.get("_http_status"))
print(res.get("tool_name"))
print(str(res.get("result", ""))[:500])
PY
```

## 18. Connector Directory

무엇인가: ChatGPT connector/plugin catalog 계열이다. 앱에서 연결 가능한 connector 목록을 OAuth로 읽는다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.chatgpt_connectors_directory_list(max_pages=1)
print(res.get("_http_status"))
print(res.get("route"))
print(res.get("apps_count"))
print([app.get("name") for app in res.get("apps", [])[:5]])
PY
```

Workspace connector directory:

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.chatgpt_connectors_directory_workspace()
print(res.get("_http_status"))
print(list(res.keys())[:10])
PY
```

## 19. Plugin / Curated Plugin Catalog

무엇인가: ChatGPT plugin/curated plugin metadata를 OAuth로 읽는 route다. 일부 list/detail route는 현재 404일 수 있으니 `_http_status`를 확인한다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
for name, call in [
    ("plugins_list", oauth.chatgpt_plugins_list),
    ("plugins_featured", oauth.chatgpt_plugins_featured),
    ("curated_plugins_export", oauth.chatgpt_curated_plugins_export),
]:
    res = call()
    print(name, res.get("_http_status"), list(res.keys())[:10])
PY
```

## 20. Codex Usage / Tasks / Environments Metadata

무엇인가: ChatGPT/Codex backend metadata다. OpenAI Platform usage/admin endpoint가 아니라 Codex 계정 surface에서 보이는 usage/task/environment 상태를 읽는다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()

usage = oauth.chatgpt_usage()
print("usage", usage.get("_http_status"), list(usage.keys())[:10])

tasks = oauth.chatgpt_tasks_list(limit=5)
print("tasks", tasks.get("_http_status"), list(tasks.keys())[:10])

envs = oauth.chatgpt_environments()
print("envs", envs.get("_http_status"), list(envs.keys())[:10])
PY
```

Repo별 environments:

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.chatgpt_environments_by_repo("openai", "codex")
print(res.get("_http_status"))
print(list(res.keys())[:10])
PY
```

## 21. Account / Site Status

무엇인가: ChatGPT backend account check, current user summary, Aura site status route다. 계정 정보는 요약만 출력한다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
for name, res in [
    ("me", oauth.chatgpt_me_summary()),
    ("accounts", oauth.chatgpt_accounts_check_summary()),
    ("aura", oauth.chatgpt_aura_site_status("https://example.com/")),
]:
    print(name, res.get("_http_status"), res.get("route"))
    print({k: v for k, v in res.items() if k.endswith("_present") or k.endswith("_count")})
PY
```

## 22. Agent Identities JWKS

무엇인가: Codex/WHAM agent identity public JWKS를 읽는다. private key가 아니라 공개 key count만 확인한다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.chatgpt_agent_identities_jwks_summary()
print(res.get("_http_status"))
print(res.get("route"))
print(res.get("keys_count"))
PY
```

## 23. Local OpenAI-Compatible Proxy

무엇인가: OAuth-only 기능을 OpenAI API 비슷한 HTTP shape로 로컬에서 받는 서버다. 외부 OpenAI API key가 필요한 앱을 이 로컬 base URL로 붙일 때 쓴다.

한 번에 proxy route를 검증하려면:

```bash
$PY bridge.py smoke --include-images
```

이미지 생성을 빼고 빠르게 보려면 `--include-images`를 생략한다.

OpenAI Python SDK로 실제 호환성을 검증하려면:

```bash
$PY bridge.py sdk-smoke --include-images
```

서버 실행:

```bash
$PY bridge.py serve --port 8787
```

다른 터미널에서 health check:

```bash
curl -s http://127.0.0.1:8787/health
```

브라우저 앱 preflight 확인:

```bash
curl -i -X OPTIONS http://127.0.0.1:8787/v1/responses \
  -H 'Origin: http://localhost:3000' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: authorization,content-type'
```

Capability boundary:

```bash
curl -s http://127.0.0.1:8787/v1/oauth-capabilities
```

Responses shape:

```bash
RESPONSE_ID=$(curl -s http://127.0.0.1:8787/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{"input":"Reply exactly: proxy response ok"}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -s http://127.0.0.1:8787/v1/responses/$RESPONSE_ID
curl -s http://127.0.0.1:8787/v1/responses/$RESPONSE_ID/input_items
curl -s -X POST http://127.0.0.1:8787/v1/responses/$RESPONSE_ID/cancel
curl -s -X DELETE http://127.0.0.1:8787/v1/responses/$RESPONSE_ID
```

OpenAI Python SDK shape:

```python
import json
from pathlib import Path

from openai import OpenAI

client = OpenAI(
    api_key="oauth-local-proxy",
    base_url="http://127.0.0.1:8787/v1",
)

print(client.models.list().data[0].id)

response = client.responses.create(
    model="gpt-5.5",
    input="Reply exactly: sdk response ok",
)
print(response.output_text)
print(client.responses.retrieve(response.id).output_text)
print(len(client.responses.input_items.list(response.id).data))
print(client.responses.cancel(response.id).status)
print(client.responses.delete(response.id))

chat = client.chat.completions.create(
    model="gpt-5.5",
    messages=[{"role": "user", "content": "Reply exactly: sdk chat ok"}],
)
print(chat.choices[0].message.content)
print(client.chat.completions.retrieve(chat.id).choices[0].message.content)
print(len(client.chat.completions.list().data))
print(client.chat.completions.update(chat.id, metadata={"source": "sdk-example"}).id)
print(client.chat.completions.messages.list(chat.id).data[0].role)
print(client.chat.completions.delete(chat.id).deleted)

for chunk in client.chat.completions.create(
    model="gpt-5.5",
    messages=[{"role": "user", "content": "Reply exactly: sdk stream chat ok"}],
    stream=True,
):
    print(chunk.choices[0].delta.content or "", end="")
print()

response_text = ""
for event in client.responses.create(
    model="gpt-5.5",
    input="Reply exactly: sdk stream response ok",
    stream=True,
):
    if event.type == "response.output_text.delta":
        response_text += event.delta
print(response_text)

embedding = client.embeddings.create(
    model="text-embedding-3-small",
    input="sdk embedding",
)
print(len(embedding.data[0].embedding))

moderation = client.moderations.create(input="hello from local moderation")
print(moderation.results[0].flagged)

batch_input = Path("artifacts/sdk_batch_input.jsonl")
batch_input.write_text(json.dumps({
    "custom_id": "moderation-1",
    "method": "POST",
    "url": "/v1/moderations",
    "body": {"input": "hello from batch moderation"},
}) + "\n")
with batch_input.open("rb") as fh:
    batch_file = client.files.create(file=fh, purpose="batch")
batch = client.batches.create(
    input_file_id=batch_file.id,
    endpoint="/v1/moderations",
    completion_window="24h",
)
print(batch.status, batch.request_counts.total)
print(len(client.files.content(batch.output_file_id).read()))
deferred = client.batches.create(
    input_file_id=batch_file.id,
    endpoint="/v1/moderations",
    completion_window="24h",
    metadata={"local_defer": "true"},
)
print(client.batches.cancel(deferred.id).status)
print(client.files.delete(batch.output_file_id).deleted)
print(client.files.delete(batch_file.id).deleted)

with open("artifacts/codex_backend_upload_probe.txt", "rb") as fh:
    uploaded = client.files.create(file=fh, purpose="assistants")
print(client.files.retrieve(uploaded.id).filename)
print(len(client.files.content(uploaded.id).read()))

upload_path = Path("artifacts/codex_backend_upload_probe.txt")
upload = client.uploads.create(
    bytes=upload_path.stat().st_size,
    filename=upload_path.name,
    mime_type="text/plain",
    purpose="assistants",
)
with upload_path.open("rb") as fh:
    upload_part = client.uploads.parts.create(upload.id, data=fh)
completed_upload = client.uploads.complete(upload.id, part_ids=[upload_part.id])
print(completed_upload.status, completed_upload.file.id)
print(client.files.delete(completed_upload.file.id).deleted)

cancel_upload = client.uploads.create(
    bytes=upload_path.stat().st_size,
    filename="cancel_upload_probe.txt",
    mime_type="text/plain",
    purpose="assistants",
)
print(client.uploads.cancel(cancel_upload.id).status)

store = client.vector_stores.create(name="sdk-local-vector")
vs_file = client.vector_stores.files.create(
    vector_store_id=store.id,
    file_id=uploaded.id,
    attributes={"source": "sdk-example"},
)
print(client.vector_stores.files.retrieve(vs_file.id, vector_store_id=store.id).status)
print(len(client.vector_stores.files.content(vs_file.id, vector_store_id=store.id).data))
batch = client.vector_stores.file_batches.create(
    vector_store_id=store.id,
    file_ids=[uploaded.id],
    attributes={"source": "sdk-batch-example"},
)
print(client.vector_stores.file_batches.retrieve(batch.id, vector_store_id=store.id).status)
print(len(client.vector_stores.file_batches.list_files(batch.id, vector_store_id=store.id).data))
print(client.vector_stores.file_batches.cancel(batch.id, vector_store_id=store.id).status)
print(client.vector_stores.files.delete(vs_file.id, vector_store_id=store.id).deleted)
print(client.files.delete(uploaded.id).deleted)
print(client.vector_stores.retrieve(store.id).id)
print(client.vector_stores.delete(store.id).deleted)

ev = client.evals.create(
    name="sdk-local-eval",
    data_source_config={"type": "custom", "item_schema": {}},
    testing_criteria=[{
        "type": "string_check",
        "name": "contains_expected",
        "input": "{{ output }}",
        "operation": "like",
        "reference": "sdk eval ok",
    }],
    metadata={
        "prompt": "Reply exactly: sdk eval ok",
        "expected_substring": "sdk eval ok",
    },
)
run = client.evals.runs.create(
    ev.id,
    name="sdk-local-eval-run",
    data_source={
        "type": "jsonl",
        "source": {
            "type": "file_content",
            "content": [{
                "item": {
                    "prompt": "Reply exactly: sdk eval ok",
                    "expected_substring": "sdk eval ok",
                }
            }],
        },
    },
)
items = client.evals.runs.output_items.list(run.id, eval_id=ev.id)
print(client.evals.runs.output_items.retrieve(items.data[0].id, eval_id=ev.id, run_id=run.id).status)
print(client.evals.runs.cancel(run.id, eval_id=ev.id).status)
print(client.evals.runs.delete(run.id, eval_id=ev.id).deleted)
print(client.evals.delete(ev.id).deleted)
```

Chat Completions shape:

```bash
CHAT_ID=$(curl -s http://127.0.0.1:8787/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Reply exactly: proxy chat ok"}]}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -s http://127.0.0.1:8787/v1/chat/completions
curl -s http://127.0.0.1:8787/v1/chat/completions/$CHAT_ID
curl -s http://127.0.0.1:8787/v1/chat/completions/$CHAT_ID/messages
curl -s http://127.0.0.1:8787/v1/chat/completions/$CHAT_ID \
  -H 'Content-Type: application/json' \
  -d '{"metadata":{"source":"curl-example"}}'
curl -s -X DELETE http://127.0.0.1:8787/v1/chat/completions/$CHAT_ID
```

Embeddings shape:

```bash
curl -s http://127.0.0.1:8787/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"input":"proxy embedding"}'
```

Moderation shape:

```bash
curl -s http://127.0.0.1:8787/v1/moderations \
  -H 'Content-Type: application/json' \
  -d '{"input":"hello from local moderation"}'
```

Image generation shape:

```bash
curl -s http://127.0.0.1:8787/v1/images/generations \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"A small green cube on a white background","response_format":"url"}'
```

Speech shape returns PCM16 bytes:

```bash
curl -s http://127.0.0.1:8787/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{"input":"oauth proxy voice ok"}' \
  > artifacts/proxy_voice.pcm16
```

Models:

```bash
curl -s http://127.0.0.1:8787/v1/models
```

Local Skills registry:

```bash
curl -s http://127.0.0.1:8787/v1/skills

SKILL_ID=$(curl -s http://127.0.0.1:8787/v1/skills \
  -H 'Content-Type: application/json' \
  -d '{"name":"local-helper","description":"Local helper skill","content":"Use this skill for local OAuth bridge checks."}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -s http://127.0.0.1:8787/v1/skills/$SKILL_ID
curl -s http://127.0.0.1:8787/v1/skills/$SKILL_ID/versions
curl -s http://127.0.0.1:8787/v1/skills/$SKILL_ID/content > artifacts/local-helper-skill.zip
curl -s -X DELETE http://127.0.0.1:8787/v1/skills/$SKILL_ID
```

Local Conversations:

```bash
CONV_ID=$(curl -s http://127.0.0.1:8787/v1/conversations \
  -H 'Content-Type: application/json' \
  -d '{"metadata":{"topic":"local-demo"},"items":[{"type":"message","role":"user","content":"Hello"}]}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

ITEM_ID=$(curl -s http://127.0.0.1:8787/v1/conversations/$CONV_ID/items \
  -H 'Content-Type: application/json' \
  -d '{"items":[{"type":"message","role":"user","content":[{"type":"input_text","text":"Second item"}]}]}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["data"][0]["id"])')

curl -s http://127.0.0.1:8787/v1/conversations/$CONV_ID
curl -s http://127.0.0.1:8787/v1/conversations/$CONV_ID/items
curl -s http://127.0.0.1:8787/v1/conversations/$CONV_ID/items/$ITEM_ID
curl -s -X DELETE http://127.0.0.1:8787/v1/conversations/$CONV_ID/items/$ITEM_ID
curl -s -X DELETE http://127.0.0.1:8787/v1/conversations/$CONV_ID
```

File upload through ChatGPT backend storage:

```bash
FILE_ID=$(curl -s http://127.0.0.1:8787/v1/files \
  -F purpose=assistants \
  -F file=@artifacts/codex_backend_upload_probe.txt \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -s http://127.0.0.1:8787/v1/files/$FILE_ID
curl -s http://127.0.0.1:8787/v1/files/$FILE_ID/content
curl -s -X DELETE http://127.0.0.1:8787/v1/files/$FILE_ID
```

Local batch shape:

```bash
printf '%s\n' '{"custom_id":"moderation-1","method":"POST","url":"/v1/moderations","body":{"input":"hello from batch moderation"}}' > artifacts/batch_input.jsonl

BATCH_FILE_ID=$(curl -s http://127.0.0.1:8787/v1/files \
  -F purpose=batch \
  -F file=@artifacts/batch_input.jsonl \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

BATCH_ID=$(curl -s http://127.0.0.1:8787/v1/batches \
  -H 'Content-Type: application/json' \
  -d "{\"input_file_id\":\"$BATCH_FILE_ID\",\"endpoint\":\"/v1/moderations\",\"completion_window\":\"24h\"}" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -s http://127.0.0.1:8787/v1/batches
curl -s http://127.0.0.1:8787/v1/batches/$BATCH_ID

DEFERRED_BATCH_ID=$(curl -s http://127.0.0.1:8787/v1/batches \
  -H 'Content-Type: application/json' \
  -d "{\"input_file_id\":\"$BATCH_FILE_ID\",\"endpoint\":\"/v1/moderations\",\"completion_window\":\"24h\",\"metadata\":{\"local_defer\":\"true\"}}" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -s -X POST http://127.0.0.1:8787/v1/batches/$DEFERRED_BATCH_ID/cancel
```

Audio transcription:

```bash
curl -s http://127.0.0.1:8787/v1/audio/transcriptions \
  -F model=gpt-4o-mini-transcribe \
  -F file=@artifacts/tiny_silence.wav
```

Local vector store:

```bash
STORE_ID=$(curl -s http://127.0.0.1:8787/v1/vector_stores \
  -H 'Content-Type: application/json' \
  -d '{"name":"oauth-local-rag"}' | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -s http://127.0.0.1:8787/v1/vector_stores/$STORE_ID/items \
  -H 'Content-Type: application/json' \
  -d '{"text":"OAuth embeddings power local vector search."}'

curl -s http://127.0.0.1:8787/v1/vector_stores/$STORE_ID/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"local vector search","limit":1}'

VS_FILE_ID=$(curl -s http://127.0.0.1:8787/v1/files \
  -F purpose=assistants \
  -F file=@artifacts/codex_backend_upload_probe.txt \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

UPLOAD_BYTES=$(wc -c < artifacts/codex_backend_upload_probe.txt | tr -d ' ')
UPLOAD_ID=$(curl -s http://127.0.0.1:8787/v1/uploads \
  -H 'Content-Type: application/json' \
  -d "{\"bytes\":$UPLOAD_BYTES,\"filename\":\"codex_backend_upload_probe.txt\",\"mime_type\":\"text/plain\",\"purpose\":\"assistants\"}" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

UPLOAD_PART_ID=$(curl -s http://127.0.0.1:8787/v1/uploads/$UPLOAD_ID/parts \
  -F data=@artifacts/codex_backend_upload_probe.txt \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -s http://127.0.0.1:8787/v1/uploads/$UPLOAD_ID/complete \
  -H 'Content-Type: application/json' \
  -d "{\"part_ids\":[\"$UPLOAD_PART_ID\"]}"

CANCEL_UPLOAD_ID=$(curl -s http://127.0.0.1:8787/v1/uploads \
  -H 'Content-Type: application/json' \
  -d "{\"bytes\":$UPLOAD_BYTES,\"filename\":\"cancel_upload_probe.txt\",\"mime_type\":\"text/plain\",\"purpose\":\"assistants\"}" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -s -X POST http://127.0.0.1:8787/v1/uploads/$CANCEL_UPLOAD_ID/cancel

curl -s http://127.0.0.1:8787/v1/vector_stores/$STORE_ID/files \
  -H 'Content-Type: application/json' \
  -d "{\"file_id\":\"$VS_FILE_ID\",\"attributes\":{\"source\":\"curl-example\"}}"

curl -s http://127.0.0.1:8787/v1/vector_stores/$STORE_ID/files
curl -s http://127.0.0.1:8787/v1/vector_stores/$STORE_ID/files/$VS_FILE_ID
curl -s http://127.0.0.1:8787/v1/vector_stores/$STORE_ID/files/$VS_FILE_ID/content

BATCH_ID=$(curl -s http://127.0.0.1:8787/v1/vector_stores/$STORE_ID/file_batches \
  -H 'Content-Type: application/json' \
  -d "{\"file_ids\":[\"$VS_FILE_ID\"],\"attributes\":{\"source\":\"curl-batch-example\"}}" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -s http://127.0.0.1:8787/v1/vector_stores/$STORE_ID/file_batches/$BATCH_ID
curl -s http://127.0.0.1:8787/v1/vector_stores/$STORE_ID/file_batches/$BATCH_ID/files
curl -s -X POST http://127.0.0.1:8787/v1/vector_stores/$STORE_ID/file_batches/$BATCH_ID/cancel

curl -s -X DELETE http://127.0.0.1:8787/v1/vector_stores/$STORE_ID/files/$VS_FILE_ID

curl -s http://127.0.0.1:8787/v1/vector_stores
curl -s http://127.0.0.1:8787/v1/vector_stores/$STORE_ID
curl -s -X DELETE http://127.0.0.1:8787/v1/vector_stores/$STORE_ID
```

Local eval:

```bash
curl -s http://127.0.0.1:8787/v1/local/evals/text_expectation \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Reply exactly: proxy eval ok","expected_substring":"proxy eval ok"}'
```

OpenAI-style local eval:

```bash
EVAL_ID=$(curl -s http://127.0.0.1:8787/v1/evals \
  -H 'Content-Type: application/json' \
  -d '{"name":"curl-local-eval","data_source_config":{"type":"custom","item_schema":{}},"testing_criteria":[{"type":"string_check","name":"contains_expected","input":"{{ output }}","operation":"like","reference":"curl eval ok"}],"metadata":{"prompt":"Reply exactly: curl eval ok","expected_substring":"curl eval ok"}}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

RUN_ID=$(curl -s http://127.0.0.1:8787/v1/evals/$EVAL_ID/runs \
  -H 'Content-Type: application/json' \
  -d '{"name":"curl-local-eval-run","data_source":{"type":"jsonl","source":{"type":"file_content","content":[{"item":{"prompt":"Reply exactly: curl eval ok","expected_substring":"curl eval ok"}}]}}}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

OUTPUT_ITEM_ID=$(curl -s http://127.0.0.1:8787/v1/evals/$EVAL_ID/runs/$RUN_ID/output_items \
  | python -c 'import json,sys; print(json.load(sys.stdin)["data"][0]["id"])')

curl -s http://127.0.0.1:8787/v1/evals
curl -s http://127.0.0.1:8787/v1/evals/$EVAL_ID
curl -s -X POST http://127.0.0.1:8787/v1/evals/$EVAL_ID \
  -H 'Content-Type: application/json' \
  -d '{"name":"curl-local-eval-updated"}'
curl -s http://127.0.0.1:8787/v1/evals/$EVAL_ID/runs
curl -s http://127.0.0.1:8787/v1/evals/$EVAL_ID/runs/$RUN_ID
curl -s http://127.0.0.1:8787/v1/evals/$EVAL_ID/runs/$RUN_ID/output_items/$OUTPUT_ITEM_ID
curl -s -X POST http://127.0.0.1:8787/v1/evals/$EVAL_ID/runs/$RUN_ID
curl -s -X DELETE http://127.0.0.1:8787/v1/evals/$EVAL_ID/runs/$RUN_ID
curl -s -X DELETE http://127.0.0.1:8787/v1/evals/$EVAL_ID
```

Fine-tuning grader preflight:

```bash
curl -s http://127.0.0.1:8787/v1/fine_tuning/alpha/graders/validate \
  -H 'Content-Type: application/json' \
  -d '{"grader":{"type":"string_check","name":"exact_label","input":"{{ sample.output_text }}","reference":"{{ item.label }}","operation":"eq"}}'

curl -s http://127.0.0.1:8787/v1/fine_tuning/alpha/graders/run \
  -H 'Content-Type: application/json' \
  -d '{"grader":{"type":"string_check","name":"exact_label","input":"{{ sample.output_text }}","reference":"{{ item.label }}","operation":"eq"},"model_sample":"approved","item":{"label":"approved"}}'
```

## 24. Official API Surface Audit

무엇인가: OpenAI 문서의 API path 목록과 현재 OAuth bridge coverage를 비교해서 `direct_official_oauth_verified`, `local_compat_or_chatgpt_backend_bridge`, `api_key_or_admin_key_required`로 분류한다.

```bash
$PY bridge.py audit
```

결과는 `reports/openai_surface_audit_latest.md`에 저장된다.

## 25. Release Preflight

무엇인가: GitHub에 올리기 전에 컴파일, 공백 오류, 필수 리포트 존재, obvious secret leak을 한 번에 확인한다. 네트워크/API 호출은 하지 않는다.

```bash
$PY bridge.py preflight
```

JSON으로 보고 싶으면:

```bash
$PY bridge.py preflight --json
```

## 26. Raw Official API Probe

무엇인가: 아직 열리는지 막히는지 직접 확인할 때 쓰는 low-level helper다. 막힌 route는 `_http_status`와 error prefix를 보고 expected blocked로 분류한다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.official_get("/v1/models")
print(res.get("_http_status"))
print(res.get("_error_prefix", "")[:300])
PY
```

## 27. Raw ChatGPT Backend Probe

무엇인가: 새 ChatGPT/Codex backend route 후보를 조심스럽게 읽기 전용으로 찔러볼 때 쓴다.

```bash
PYTHONPATH=src $PY - <<'PY'
from openai_oauth_access import OpenAIOAuthAccess

oauth = OpenAIOAuthAccess()
res = oauth.chatgpt_backend_get("/wham/usage")
print(res.get("_http_status"))
print(list(res.keys())[:10])
PY
```

## 확인된 경계

이 예시들이 "OpenAI Platform endpoint가 전부 OAuth로 뚫렸다"는 뜻은 아니다. 실제 경계는 다음처럼 봐야 한다.

- 텍스트/챗: Codex OAuth route로 처리 가능.
- 이미지/그림: Codex OAuth image_generation tool로 처리 가능.
- STT: 공식 `/v1/audio/transcriptions`가 OAuth로 가능.
- TTS: 공식 `/v1/audio/speech`는 막힘. Realtime audio로 PCM16 생성 가능.
- Embeddings: 공식 `/v1/embeddings`가 OAuth로 가능.
- Files: Platform `/v1/files`가 아니라 ChatGPT backend `/backend-api/files`가 OAuth로 가능.
- Vector stores: hosted vector store는 막힘. 로컬 store + OAuth embeddings로 기능 대체.
- Evals: hosted eval은 막힘. 로컬 eval runner + Codex text로 기능 대체.
- Realtime WebSocket/client secret/transcription session: OAuth로 가능.
- Realtime translation client secret: OAuth로 가능.
- Realtime WebRTC call: OAuth auth는 통과, 실제 사용은 브라우저 SDP offer 필요.
- Hosted `/v1/conversations`: OAuth가 route validation까지 도달했지만 현재 probe는 project ID 요구에서 멈춘다. 로컬 `/v1/conversations` 호환 저장소는 별도로 제공한다.
- Admin/Usage/Fine-tuning/Videos/hosted Containers/hosted ChatKit sessions/hosted ChatKit threads/custom voices/hosted Skills: OpenAI Platform 서버 리소스라 Codex OAuth로 그대로 만들 수 있는 route는 아직 확인되지 않았다. Containers, ChatKit, Skills는 로컬 호환 레이어만 제공한다.
