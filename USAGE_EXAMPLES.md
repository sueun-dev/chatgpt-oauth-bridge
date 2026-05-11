# OAuth Usage Examples

이 문서는 지금 이 폴더에서 실제로 만든 OAuth-only 래퍼를 어떻게 쓰는지에 대한 예시다. 전제는 하나다: `OPENAI_API_KEY` 없이 Codex/ChatGPT OAuth 토큰만 쓴다.

먼저 터미널에서 이걸 잡고 시작한다.

```bash
cd chatgpt-oauth-bridge
export PYTHONPATH=src
PY=python
```

토큰은 출력하지 않는다. Hermes 토큰이 만료되어 있으면 `src/codex_oauth.py`가 현재 Codex CLI OAuth 토큰으로 fallback한다.

연결 상태부터 보고 싶으면:

```bash
python setup_oauth.py
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

## 12. ChatGPT/Codex Backend File Upload

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

## 13. Local Vector Store / RAG 대체

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

## 14. Local Eval 대체

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

## 15. Codex Apps MCP Tools Inventory

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

## 16. Codex Apps GitHub Public Search

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

## 17. Connector Directory

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

## 18. Plugin / Curated Plugin Catalog

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

## 19. Codex Usage / Tasks / Environments Metadata

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

## 20. Account / Site Status

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

## 21. Agent Identities JWKS

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

## 22. Local OpenAI-Compatible Proxy

무엇인가: OAuth-only 기능을 OpenAI API 비슷한 HTTP shape로 로컬에서 받는 서버다. 외부 OpenAI API key가 필요한 앱을 이 로컬 base URL로 붙일 때 쓴다.

서버 실행:

```bash
PYTHONPATH=src $PY src/oauth_openai_compat_server.py --port 8787
```

다른 터미널에서 health check:

```bash
curl -s http://127.0.0.1:8787/health
```

Responses shape:

```bash
curl -s http://127.0.0.1:8787/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{"input":"Reply exactly: proxy response ok"}'
```

Chat Completions shape:

```bash
curl -s http://127.0.0.1:8787/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Reply exactly: proxy chat ok"}]}'
```

Embeddings shape:

```bash
curl -s http://127.0.0.1:8787/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"input":"proxy embedding"}'
```

Image generation shape:

```bash
curl -s http://127.0.0.1:8787/v1/images/generations \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"A small green cube on a white background","response_format":"url"}'
```

## 23. Raw Official API Probe

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

## 24. Raw ChatGPT Backend Probe

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
- Realtime WebRTC call: OAuth auth는 통과, 실제 사용은 브라우저 SDP offer 필요.
- Admin/Usage/Fine-tuning/Containers/Videos/hosted ChatKit sessions: OpenAI Platform 서버 리소스라 Codex OAuth로 그대로 만들 수 있는 route는 아직 확인되지 않았다.
