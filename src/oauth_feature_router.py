from __future__ import annotations

import json
import math
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from openai_oauth_access import OpenAIOAuthAccess


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LOCAL_FILES = DATA / "files"
LOCAL_VECTORS = DATA / "vector_stores"


class OAuthFeatureRouter:
    """
    Compatibility layer for OpenAI-like workflows that can be handled with the
    OAuth surfaces that actually passed locally.

    This is not claiming blocked Platform API endpoints became available. It
    routes the function to Codex OAuth, Realtime OAuth, embeddings OAuth, or
    local storage where that is the honest implementation.
    """

    def __init__(self) -> None:
        self.oauth = OpenAIOAuthAccess()
        DATA.mkdir(exist_ok=True)
        LOCAL_FILES.mkdir(exist_ok=True)
        LOCAL_VECTORS.mkdir(exist_ok=True)

    def responses_create(self, input: str, *, instructions: str = "Answer directly.") -> Dict[str, Any]:
        text = self.oauth.codex_text(input, instructions=instructions)
        return {
            "object": "oauth_compat.response",
            "route": "codex_text",
            "model": self.oauth.text_model,
            "output_text": text,
        }

    def chat_completions_create(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        transcript = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)
        text = self.oauth.codex_text(
            transcript,
            instructions="Continue this chat as the assistant. Return only the assistant message.",
        )
        return {
            "object": "oauth_compat.chat.completion",
            "route": "codex_text",
            "model": self.oauth.text_model,
            "message": {"role": "assistant", "content": text},
        }

    def images_generate(self, prompt: str, output_path: Path | str, *, size: str = "1024x1024") -> Dict[str, Any]:
        path = self.oauth.codex_generate_image(prompt, output_path, size=size)
        return {
            "object": "oauth_compat.image",
            "route": "codex_image_generation",
            "size": size,
            "path": str(path),
        }

    def audio_speech_create(self, text: str, output_path: Path | str) -> Dict[str, Any]:
        path = self.oauth.realtime_say_to_pcm(text, output_path)
        return {
            "object": "oauth_compat.audio.speech",
            "route": "realtime_websocket_audio",
            "format": "pcm16",
            "path": str(path),
            "bytes": Path(path).stat().st_size,
        }

    def audio_transcriptions_create(self, audio_path: Path | str) -> Dict[str, Any]:
        payload = self.oauth.official_transcribe_audio(audio_path)
        payload["route"] = "official_audio_transcriptions"
        return payload

    def embeddings_create(self, text: str) -> Dict[str, Any]:
        payload = self.oauth.official_embedding(text)
        payload["route"] = "official_embeddings"
        return payload

    def files_create(self, path: Path | str, *, purpose: str = "assistants") -> Dict[str, Any]:
        src = Path(path)
        uploaded = self.oauth.chatgpt_upload_file(src)
        if uploaded.get("_http_status", 200) >= 400:
            return uploaded
        file_id = str(uploaded["id"])
        dst = LOCAL_FILES / file_id
        dst.mkdir()
        record = {
            "id": file_id,
            "object": "oauth_compat.file",
            "route": "chatgpt_backend_files",
            "uri": uploaded.get("uri"),
            "filename": uploaded.get("filename") or src.name,
            "purpose": purpose,
            "bytes": uploaded.get("bytes"),
            "mime_type": uploaded.get("mime_type"),
            "created_at": int(time.time()),
            "download_url_present": uploaded.get("download_url_present"),
            "download_url_host": uploaded.get("download_url_host"),
            "local_metadata_path": str(dst / "metadata.json"),
        }
        (dst / "metadata.json").write_text(json.dumps(record, indent=2, sort_keys=True))
        return record

    def files_list(self) -> Dict[str, Any]:
        records = []
        for meta in sorted(LOCAL_FILES.glob("*/metadata.json")):
            records.append(json.loads(meta.read_text()))
        return {"object": "oauth_compat.list", "route": "local_file_metadata", "data": records}

    def vector_stores_create(self, *, name: str) -> Dict[str, Any]:
        store_id = f"vs-local-{uuid.uuid4().hex}"
        path = LOCAL_VECTORS / f"{store_id}.json"
        record = {
            "id": store_id,
            "object": "oauth_compat.vector_store",
            "route": "local_vector_store_plus_oauth_embeddings",
            "name": name,
            "created_at": int(time.time()),
            "items": [],
        }
        path.write_text(json.dumps(record, indent=2, sort_keys=True))
        return {k: v for k, v in record.items() if k != "items"}

    def vector_stores_add_text(self, store_id: str, text: str, *, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        store = self._load_vector_store(store_id)
        vector = self._embedding_vector(text)
        item = {
            "id": f"vsi-local-{uuid.uuid4().hex}",
            "text": text,
            "metadata": metadata or {},
            "embedding": vector,
            "created_at": int(time.time()),
        }
        store["items"].append(item)
        self._save_vector_store(store)
        return {
            "id": item["id"],
            "object": "oauth_compat.vector_store.item",
            "route": "local_vector_store_plus_oauth_embeddings",
            "store_id": store_id,
        }

    def vector_stores_search(self, store_id: str, query: str, *, limit: int = 5) -> Dict[str, Any]:
        store = self._load_vector_store(store_id)
        query_vector = self._embedding_vector(query)
        scored = []
        for item in store["items"]:
            score = self._cosine(query_vector, item["embedding"])
            scored.append({
                "id": item["id"],
                "score": score,
                "text": item["text"],
                "metadata": item["metadata"],
            })
        scored.sort(key=lambda item: item["score"], reverse=True)
        return {
            "object": "oauth_compat.vector_store.search_results",
            "route": "local_vector_store_plus_oauth_embeddings",
            "store_id": store_id,
            "data": scored[:limit],
        }

    def eval_text_expectation(self, prompt: str, expected_substring: str) -> Dict[str, Any]:
        output = self.responses_create(prompt)["output_text"]
        return {
            "object": "oauth_compat.eval",
            "route": "local_eval_plus_codex_text",
            "passed": expected_substring.lower() in output.lower(),
            "output_text": output,
            "expected_substring": expected_substring,
        }

    def _embedding_vector(self, text: str) -> List[float]:
        payload = self.embeddings_create(text)
        data = payload.get("data")
        if not isinstance(data, list) or not data:
            raise RuntimeError(f"Embedding response did not contain data: {payload}")
        vector = data[0].get("embedding") if isinstance(data[0], dict) else None
        if not isinstance(vector, list):
            raise RuntimeError("Embedding response did not contain a vector.")
        return [float(x) for x in vector]

    def _vector_path(self, store_id: str) -> Path:
        return LOCAL_VECTORS / f"{store_id}.json"

    def _load_vector_store(self, store_id: str) -> Dict[str, Any]:
        path = self._vector_path(store_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local vector store: {store_id}")
        return json.loads(path.read_text())

    def _save_vector_store(self, store: Dict[str, Any]) -> None:
        self._vector_path(store["id"]).write_text(json.dumps(store, indent=2, sort_keys=True))

    def _cosine(self, left: Iterable[float], right: Iterable[float]) -> float:
        left_values = list(left)
        right_values = list(right)
        dot = sum(a * b for a, b in zip(left_values, right_values))
        left_norm = math.sqrt(sum(a * a for a in left_values))
        right_norm = math.sqrt(sum(b * b for b in right_values))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)


def main() -> int:
    router = OAuthFeatureRouter()
    response = router.responses_create("Reply with exactly: oauth compat ok")
    store = router.vector_stores_create(name="oauth-compat-smoke")
    router.vector_stores_add_text(store["id"], "OAuth embeddings can power local vector search.")
    search = router.vector_stores_search(store["id"], "local vector search")
    print(json.dumps({
        "response_text": response["output_text"],
        "vector_store_id": store["id"],
        "top_vector_score": search["data"][0]["score"] if search["data"] else None,
        "routes": [
            "codex_text",
            "codex_image_generation",
            "realtime_websocket_audio",
            "official_audio_transcriptions",
            "official_embeddings",
            "chatgpt_backend_files",
            "local_vector_store_plus_oauth_embeddings",
            "local_eval_plus_codex_text",
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
