from __future__ import annotations

import argparse
import json
import threading
import time
import wave
from pathlib import Path
from typing import Any, Callable, Dict

import httpx

from oauth_feature_router import ROOT
from oauth_openai_compat_server import make_server


REPORTS = ROOT / "reports"
ARTIFACTS = ROOT / "artifacts"


class ProxySmoke:
    def __init__(self, *, include_speech: bool, include_images: bool) -> None:
        self.include_speech = include_speech
        self.include_images = include_images
        self.rows: list[Dict[str, Any]] = []

    def record(
        self,
        name: str,
        response: httpx.Response,
        *,
        expect_binary: bool = False,
        expect_status: int | None = None,
        expect_binary_min_bytes: int = 100,
        expect: Callable[[Any, Dict[str, Any], httpx.Response], bool] | None = None,
    ) -> Dict[str, Any]:
        row: Dict[str, Any] = {
            "name": name,
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "access_control_allow_origin": response.headers.get("access-control-allow-origin"),
            "access_control_allow_methods": response.headers.get("access-control-allow-methods"),
            "access_control_allow_headers": response.headers.get("access-control-allow-headers"),
        }
        if expect_binary:
            row["bytes"] = len(response.content)
            wanted_status = expect_status or 200
            row["status"] = "pass" if response.status_code == wanted_status and len(response.content) >= expect_binary_min_bytes else "fail"
        else:
            try:
                payload = response.json()
            except Exception:
                payload = None
            if isinstance(payload, dict):
                row["object"] = payload.get("object")
                row["route"] = payload.get("oauth_compat_route") or payload.get("route")
                error = payload.get("error")
                if isinstance(error, dict):
                    row["error_type"] = error.get("type")
                data = payload.get("data")
                if isinstance(data, list):
                    row["data_count"] = len(data)
                if isinstance(payload.get("id"), str):
                    row["id_prefix"] = payload["id"][:18]
                if isinstance(payload.get("status"), str):
                    row["resource_status"] = payload["status"]
                if isinstance(payload.get("category"), str):
                    row["category"] = payload["category"]
                if isinstance(payload.get("matched_path"), str):
                    row["matched_path"] = payload["matched_path"]
                if isinstance(payload.get("match_type"), str):
                    row["match_type"] = payload["match_type"]
                if isinstance(payload.get("passed"), bool):
                    row["passed"] = payload["passed"]
                if isinstance(payload.get("deleted"), bool):
                    row["deleted"] = payload["deleted"]
                if isinstance(payload.get("output_text"), str):
                    row["output_text_len"] = len(payload["output_text"])
                file_counts = payload.get("file_counts")
                if isinstance(file_counts, dict) and isinstance(file_counts.get("total"), int):
                    row["file_counts_total"] = file_counts["total"]
                file_payload = payload.get("file")
                if isinstance(file_payload, dict) and isinstance(file_payload.get("id"), str):
                    row["file_id_prefix"] = file_payload["id"][:18]
                if isinstance(payload.get("part_count"), int):
                    row["part_count"] = payload["part_count"]
                if isinstance(payload.get("output_file_id"), str):
                    row["output_file_id_prefix"] = payload["output_file_id"][:18]
                request_counts = payload.get("request_counts")
                if isinstance(request_counts, dict) and isinstance(request_counts.get("total"), int):
                    row["request_counts_total"] = request_counts["total"]
                result_counts = payload.get("result_counts")
                if isinstance(result_counts, dict) and isinstance(result_counts.get("total"), int):
                    row["result_counts_total"] = result_counts["total"]
                results = payload.get("results")
                if isinstance(results, list):
                    row["results_count"] = len(results)
                    if results and isinstance(results[0], dict) and isinstance(results[0].get("flagged"), bool):
                        row["flagged"] = results[0]["flagged"]
                choices = payload.get("choices")
                if isinstance(choices, list):
                    row["choices_count"] = len(choices)
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    embedding = data[0].get("embedding")
                    if isinstance(embedding, list):
                        row["embedding_dims"] = len(embedding)
                local_path = payload.get("local_path")
                if isinstance(local_path, str):
                    row["local_path_present"] = Path(local_path).exists()
            ok = response.status_code == expect_status if expect_status is not None else response.status_code < 400
            if expect is not None:
                try:
                    ok = ok and expect(payload, row, response)
                except Exception as exc:
                    row["validator_error"] = f"{type(exc).__name__}: {exc}"
                    ok = False
            row["status"] = "pass" if ok else "fail"
        self.rows.append(row)
        print(f"[{row['status']}] {name}")
        return row

    def tiny_wav(self) -> Path:
        path = ARTIFACTS / "tiny_silence.wav"
        ARTIFACTS.mkdir(exist_ok=True)
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x00" * 1600)
        return path

    def record_sse(self, name: str, response: httpx.Response, *, expect_done: bool = True) -> None:
        text = response.text
        row: Dict[str, Any] = {
            "name": name,
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "access_control_allow_origin": response.headers.get("access-control-allow-origin"),
            "sse_events": text.count("\n\n"),
            "done_present": "[DONE]" in text,
        }
        row["status"] = "pass" if response.status_code == 200 and row["sse_events"] > 0 and (row["done_present"] or not expect_done) else "fail"
        self.rows.append(row)
        print(f"[{row['status']}] {name}")

    def json_payload(self, response: httpx.Response) -> Dict[str, Any]:
        try:
            payload = response.json()
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def json_value(self, response: httpx.Response, key: str, default: str = "") -> str:
        value = self.json_payload(response).get(key)
        return value if isinstance(value, str) else default

    def first_data_id(self, response: httpx.Response) -> str:
        data = self.json_payload(response).get("data")
        if isinstance(data, list) and data and isinstance(data[0], dict):
            value = data[0].get("id")
            return value if isinstance(value, str) else ""
        return ""

    def nested_file_id(self, response: httpx.Response) -> str:
        file_payload = self.json_payload(response).get("file")
        if isinstance(file_payload, dict):
            value = file_payload.get("id")
            return value if isinstance(value, str) else ""
        return ""

    def run(self, base_url: str, *, write: bool = True) -> int:
        client = httpx.Client(timeout=httpx.Timeout(120.0))
        self.record("health", client.get(f"{base_url}/health"))
        self.record("capabilities", client.get(f"{base_url}/v1/oauth-capabilities"))
        self.record(
            "cors_preflight_responses",
            client.options(
                f"{base_url}/v1/responses",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization,content-type",
                },
            ),
            expect_status=204,
            expect=lambda payload, row, response: row.get("access_control_allow_origin") == "*"
            and "POST" in str(row.get("access_control_allow_methods"))
            and "Authorization" in str(row.get("access_control_allow_headers")),
        )
        models = client.get(f"{base_url}/v1/models")
        self.record("models", models)
        model_id = self.first_data_id(models)
        self.record(
            "models_retrieve",
            client.get(f"{base_url}/v1/models/{model_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == model_id
            and payload.get("object") == "model",
        )
        assistant = client.post(
            f"{base_url}/v1/assistants",
            json={
                "model": "gpt-5.5",
                "name": "proxy-local-assistant",
                "instructions": "Reply briefly.",
            },
        )
        self.record(
            "assistants_create",
            assistant,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and str(payload.get("id", "")).startswith("asst_local_")
            and payload.get("object") == "assistant",
        )
        assistant_id = self.json_value(assistant, "id")
        self.record("assistants_list", client.get(f"{base_url}/v1/assistants"), expect=lambda payload, row, response: row.get("data_count", 0) > 0)
        self.record(
            "assistants_retrieve",
            client.get(f"{base_url}/v1/assistants/{assistant_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict) and payload.get("id") == assistant_id,
        )
        self.record(
            "assistants_update",
            client.post(f"{base_url}/v1/assistants/{assistant_id}", json={"name": "proxy-local-assistant-updated"}),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == assistant_id
            and payload.get("name") == "proxy-local-assistant-updated",
        )
        thread_response = client.post(
            f"{base_url}/v1/threads",
            json={"messages": [{"role": "user", "content": "Reply exactly: assistant proxy ok"}]},
        )
        self.record(
            "threads_create",
            thread_response,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and str(payload.get("id", "")).startswith("thread_local_")
            and payload.get("object") == "thread",
        )
        thread_id = self.json_value(thread_response, "id")
        self.record(
            "threads_retrieve",
            client.get(f"{base_url}/v1/threads/{thread_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict) and payload.get("id") == thread_id,
        )
        self.record(
            "threads_update",
            client.post(f"{base_url}/v1/threads/{thread_id}", json={"metadata": {"source": "proxy-smoke"}}),
            expect=lambda payload, row, response: isinstance(payload, dict) and payload.get("id") == thread_id,
        )
        thread_message = client.post(
            f"{base_url}/v1/threads/{thread_id}/messages",
            json={"role": "user", "content": "Reply exactly: assistant message ok"},
        )
        self.record(
            "thread_messages_create",
            thread_message,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and str(payload.get("id", "")).startswith("msg_local_")
            and payload.get("object") == "thread.message",
        )
        message_id = self.json_value(thread_message, "id")
        self.record("thread_messages_list", client.get(f"{base_url}/v1/threads/{thread_id}/messages"), expect=lambda payload, row, response: row.get("data_count", 0) >= 1)
        self.record(
            "thread_messages_retrieve",
            client.get(f"{base_url}/v1/threads/{thread_id}/messages/{message_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict) and payload.get("id") == message_id,
        )
        self.record(
            "thread_messages_update",
            client.post(f"{base_url}/v1/threads/{thread_id}/messages/{message_id}", json={"metadata": {"source": "proxy-smoke"}}),
            expect=lambda payload, row, response: isinstance(payload, dict) and payload.get("id") == message_id,
        )
        thread_run = client.post(
            f"{base_url}/v1/threads/{thread_id}/runs",
            json={"assistant_id": assistant_id},
        )
        self.record(
            "thread_runs_create",
            thread_run,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and str(payload.get("id", "")).startswith("run_local_")
            and payload.get("object") == "thread.run"
            and row.get("resource_status") == "completed",
        )
        run_id = self.json_value(thread_run, "id")
        self.record("thread_runs_list", client.get(f"{base_url}/v1/threads/{thread_id}/runs"), expect=lambda payload, row, response: row.get("data_count", 0) >= 1)
        self.record(
            "thread_runs_retrieve",
            client.get(f"{base_url}/v1/threads/{thread_id}/runs/{run_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict) and payload.get("id") == run_id,
        )
        self.record(
            "thread_runs_update",
            client.post(f"{base_url}/v1/threads/{thread_id}/runs/{run_id}", json={"metadata": {"source": "proxy-smoke"}}),
            expect=lambda payload, row, response: isinstance(payload, dict) and payload.get("id") == run_id,
        )
        run_steps = client.get(f"{base_url}/v1/threads/{thread_id}/runs/{run_id}/steps")
        self.record("thread_run_steps_list", run_steps, expect=lambda payload, row, response: row.get("data_count") == 1)
        step_id = self.first_data_id(run_steps)
        self.record(
            "thread_run_steps_retrieve",
            client.get(f"{base_url}/v1/threads/{thread_id}/runs/{run_id}/steps/{step_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict) and payload.get("id") == step_id,
        )
        self.record(
            "thread_runs_cancel",
            client.post(f"{base_url}/v1/threads/{thread_id}/runs/{run_id}/cancel"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == run_id
            and row.get("resource_status") == "cancelled",
        )
        create_and_run = client.post(
            f"{base_url}/v1/threads/runs",
            json={
                "assistant_id": assistant_id,
                "thread": {"messages": [{"role": "user", "content": "Reply exactly: create and run ok"}]},
            },
        )
        self.record(
            "threads_create_and_run",
            create_and_run,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and str(payload.get("id", "")).startswith("run_local_")
            and row.get("resource_status") == "completed",
        )
        self.record(
            "thread_messages_delete",
            client.delete(f"{base_url}/v1/threads/{thread_id}/messages/{message_id}"),
            expect=lambda payload, row, response: row.get("deleted") is True,
        )
        self.record(
            "threads_delete",
            client.delete(f"{base_url}/v1/threads/{thread_id}"),
            expect=lambda payload, row, response: row.get("deleted") is True,
        )
        self.record(
            "assistants_delete",
            client.delete(f"{base_url}/v1/assistants/{assistant_id}"),
            expect=lambda payload, row, response: row.get("deleted") is True,
        )
        created_response = client.post(
            f"{base_url}/v1/responses",
            json={"input": "Reply exactly: proxy responses ok"},
        )
        self.record(
            "responses",
            created_response,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and isinstance(payload.get("output_text"), str)
            and bool(payload["output_text"].strip()),
        )
        response_id = self.json_value(created_response, "id")
        self.record(
            "responses_retrieve",
            client.get(f"{base_url}/v1/responses/{response_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == response_id
            and payload.get("object") == "response",
        )
        self.record(
            "responses_input_items",
            client.get(f"{base_url}/v1/responses/{response_id}/input_items"),
            expect=lambda payload, row, response: row.get("data_count") == 1,
        )
        self.record(
            "responses_cancel",
            client.post(f"{base_url}/v1/responses/{response_id}/cancel"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == response_id
            and row.get("resource_status") == "cancelled",
        )
        self.record(
            "responses_delete",
            client.delete(f"{base_url}/v1/responses/{response_id}"),
            expect_status=204,
        )
        self.record_sse(
            "responses_stream",
            client.post(
                f"{base_url}/v1/responses",
                json={"input": "Reply exactly: proxy responses stream ok", "stream": True},
            ),
        )
        self.record(
            "responses_input_tokens_estimate",
            client.post(
                f"{base_url}/v1/responses/input_tokens",
                json={"input": "Count this local proxy prompt."},
            ),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("estimated") is True
            and isinstance(payload.get("input_tokens"), int)
            and payload["input_tokens"] > 0,
        )
        self.record(
            "responses_compact",
            client.post(
                f"{base_url}/v1/responses/compact",
                json={"input": "Compact this local proxy prompt and preserve compact-ok."},
            ),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("object") == "response.compaction"
            and isinstance(payload.get("output"), list)
            and len(payload["output"]) == 1,
        )
        self.record(
            "completions",
            client.post(
                f"{base_url}/v1/completions",
                json={"prompt": "Reply exactly: proxy legacy completions ok"},
            ),
            expect=lambda payload, row, response: row.get("choices_count") == 1,
        )
        self.record_sse(
            "completions_stream",
            client.post(
                f"{base_url}/v1/completions",
                json={"prompt": "Reply exactly: proxy legacy completions stream ok", "stream": True},
            ),
        )
        created_chat = client.post(
            f"{base_url}/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "Reply exactly: proxy chat ok"}]},
        )
        self.record(
            "chat_completions",
            created_chat,
            expect=lambda payload, row, response: row.get("choices_count") == 1,
        )
        chat_id = self.json_value(created_chat, "id")
        self.record(
            "chat_completions_retrieve",
            client.get(f"{base_url}/v1/chat/completions/{chat_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == chat_id
            and payload.get("object") == "chat.completion",
        )
        self.record(
            "chat_completions_list",
            client.get(f"{base_url}/v1/chat/completions"),
            expect=lambda payload, row, response: row.get("data_count", 0) > 0,
        )
        self.record(
            "chat_completions_update",
            client.post(f"{base_url}/v1/chat/completions/{chat_id}", json={"metadata": {"source": "proxy-smoke"}}),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == chat_id,
        )
        self.record(
            "chat_completion_messages",
            client.get(f"{base_url}/v1/chat/completions/{chat_id}/messages"),
            expect=lambda payload, row, response: row.get("data_count") == 1,
        )
        self.record(
            "chat_completions_delete",
            client.delete(f"{base_url}/v1/chat/completions/{chat_id}"),
            expect=lambda payload, row, response: row.get("deleted") is True,
        )
        self.record_sse(
            "chat_completions_stream",
            client.post(
                f"{base_url}/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "Reply exactly: proxy chat stream ok"}], "stream": True},
            ),
        )
        self.record(
            "chat_bad_request",
            client.post(
                f"{base_url}/v1/chat/completions",
                json={"messages": "not-a-list"},
            ),
            expect_status=400,
            expect=lambda payload, row, response: row.get("error_type") == "bad_request",
        )
        video_response = client.post(
            f"{base_url}/v1/videos",
            json={"prompt": "Proxy smoke storyboard", "model": "sora-2", "seconds": 4},
        )
        try:
            video_id = str(video_response.json().get("id") or "")
        except Exception:
            video_id = ""
        self.record(
            "videos_create",
            video_response,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("object") == "video"
            and payload.get("hosted_video_created") is False,
        )
        self.record(
            "videos_list",
            client.get(f"{base_url}/v1/videos"),
            expect=lambda payload, row, response: row.get("data_count", 0) >= 1,
        )
        if video_id:
            self.record(
                "videos_retrieve",
                client.get(f"{base_url}/v1/videos/{video_id}"),
                expect=lambda payload, row, response: isinstance(payload, dict)
                and payload.get("id") == video_id,
            )
            self.record(
                "videos_content_manifest",
                client.get(f"{base_url}/v1/videos/{video_id}/content"),
                expect=lambda payload, row, response: isinstance(payload, dict)
                and payload.get("object") == "video.local_content_manifest"
                and payload.get("hosted_video_bytes") is False,
            )
            self.record(
                "videos_remix",
                client.post(f"{base_url}/v1/videos/{video_id}/remix", json={"prompt": "Proxy smoke remix"}),
                expect=lambda payload, row, response: isinstance(payload, dict)
                and payload.get("operation") == "remix"
                and payload.get("source_video_id") == video_id,
            )
            self.record(
                "videos_delete",
                client.delete(f"{base_url}/v1/videos/{video_id}"),
                expect=lambda payload, row, response: row.get("deleted") is True,
            )
        self.record(
            "video_characters_list",
            client.get(f"{base_url}/v1/videos/characters"),
            expect=lambda payload, row, response: row.get("data_count", 0) >= 1,
        )
        self.record(
            "video_character_retrieve",
            client.get(f"{base_url}/v1/videos/characters/vchar-local-default"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == "vchar-local-default",
        )
        self.record(
            "embeddings",
            client.post(
                f"{base_url}/v1/embeddings",
                json={"input": "OAuth proxy embedding smoke"},
            ),
            expect=lambda payload, row, response: isinstance(row.get("embedding_dims"), int)
            and row["embedding_dims"] > 100,
        )
        if self.include_images:
            self.record(
                "images_generations",
                client.post(
                    f"{base_url}/v1/images/generations",
                    json={
                        "prompt": "A small clean icon of an OAuth bridge on a white background, no text",
                        "size": "1024x1024",
                    },
                ),
                expect=lambda payload, row, response: row.get("data_count") == 1
                and row.get("local_path_present") is True,
            )
        self.record("files_list_before", client.get(f"{base_url}/v1/files"))

        probe = ARTIFACTS / "codex_backend_upload_probe.txt"
        ARTIFACTS.mkdir(exist_ok=True)
        probe.write_text("OAuth proxy smoke upload. No secrets.\n")
        with probe.open("rb") as fh:
            created_file = client.post(
                f"{base_url}/v1/files",
                files={"file": ("proxy_upload.txt", fh, "text/plain")},
                data={"purpose": "assistants"},
            )
            self.record(
                "files_create",
                created_file,
                expect=lambda payload, row, response: isinstance(payload, dict)
                and isinstance(payload.get("id"), str)
                and bool(payload.get("filename")),
            )
        file_id = self.json_value(created_file, "id")
        self.record(
            "files_retrieve",
            client.get(f"{base_url}/v1/files/{file_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == file_id
            and payload.get("object") == "file",
        )
        self.record(
            "files_content",
            client.get(f"{base_url}/v1/files/{file_id}/content"),
            expect_binary=True,
            expect_binary_min_bytes=1,
        )
        self.record("files_list_after", client.get(f"{base_url}/v1/files"))

        self.record(
            "moderations",
            client.post(
                f"{base_url}/v1/moderations",
                json={"input": "hello from local moderation"},
            ),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and row.get("results_count") == 1
            and row.get("flagged") is False,
        )

        upload_content = b"OAuth proxy uploads part content. No secrets.\n"
        created_upload = client.post(
            f"{base_url}/v1/uploads",
            json={
                "bytes": len(upload_content),
                "filename": "proxy_uploads_probe.txt",
                "mime_type": "text/plain",
                "purpose": "assistants",
            },
        )
        self.record(
            "uploads_create",
            created_upload,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and str(payload.get("id", "")).startswith("upload-local-")
            and payload.get("object") == "upload"
            and row.get("resource_status") == "pending",
        )
        upload_id = self.json_value(created_upload, "id")
        created_part = client.post(
            f"{base_url}/v1/uploads/{upload_id}/parts",
            files={"data": ("proxy_uploads_probe.part", upload_content, "text/plain")},
        )
        self.record(
            "upload_parts_create",
            created_part,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and str(payload.get("id", "")).startswith("uploadpart-local-")
            and payload.get("object") == "upload.part"
            and payload.get("upload_id") == upload_id,
        )
        upload_part_id = self.json_value(created_part, "id")
        completed_upload = client.post(
            f"{base_url}/v1/uploads/{upload_id}/complete",
            json={"part_ids": [upload_part_id]},
        )
        self.record(
            "uploads_complete",
            completed_upload,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == upload_id
            and row.get("resource_status") == "completed"
            and isinstance(payload.get("file"), dict)
            and str(payload["file"].get("id", "")).startswith("file_"),
        )
        completed_upload_file_id = self.nested_file_id(completed_upload)
        if isinstance(completed_upload_file_id, str):
            self.record(
                "uploads_completed_file_delete",
                client.delete(f"{base_url}/v1/files/{completed_upload_file_id}"),
                expect=lambda payload, row, response: row.get("deleted") is True,
            )
        cancel_upload = client.post(
            f"{base_url}/v1/uploads",
            json={
                "bytes": len(upload_content),
                "filename": "proxy_cancel_uploads_probe.txt",
                "mime_type": "text/plain",
                "purpose": "assistants",
            },
        )
        self.record("uploads_cancel_create", cancel_upload)
        cancel_upload_id = self.json_value(cancel_upload, "id")
        self.record(
            "uploads_cancel",
            client.post(f"{base_url}/v1/uploads/{cancel_upload_id}/cancel"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == cancel_upload_id
            and row.get("resource_status") == "cancelled",
        )

        batch_input = ARTIFACTS / "proxy_batch_input.jsonl"
        batch_input.write_text(json.dumps({
            "custom_id": "proxy-moderation-1",
            "method": "POST",
            "url": "/v1/moderations",
            "body": {"input": "hello from proxy batch moderation"},
        }) + "\n")
        with batch_input.open("rb") as fh:
            batch_input_file = client.post(
                f"{base_url}/v1/files",
                files={"file": ("proxy_batch_input.jsonl", fh, "application/jsonl")},
                data={"purpose": "batch"},
            )
        self.record(
            "batch_input_file_create",
            batch_input_file,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and isinstance(payload.get("id"), str),
        )
        batch_input_file_id = self.json_value(batch_input_file, "id")
        created_batch = client.post(
            f"{base_url}/v1/batches",
            json={
                "input_file_id": batch_input_file_id,
                "endpoint": "/v1/moderations",
                "completion_window": "24h",
            },
        )
        self.record(
            "batches_create",
            created_batch,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and str(payload.get("id", "")).startswith("batch-local-")
            and row.get("resource_status") == "completed"
            and row.get("request_counts_total") == 1
            and isinstance(payload.get("output_file_id"), str),
        )
        batch_id = self.json_value(created_batch, "id")
        output_file_id = self.json_value(created_batch, "output_file_id")
        self.record("batches_list", client.get(f"{base_url}/v1/batches"), expect=lambda payload, row, response: row.get("data_count", 0) > 0)
        self.record(
            "batches_retrieve",
            client.get(f"{base_url}/v1/batches/{batch_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == batch_id
            and payload.get("object") == "batch",
        )
        if isinstance(output_file_id, str):
            self.record(
                "batches_output_file_content",
                client.get(f"{base_url}/v1/files/{output_file_id}/content"),
                expect_binary=True,
                expect_binary_min_bytes=10,
            )
            self.record(
                "batches_output_file_delete",
                client.delete(f"{base_url}/v1/files/{output_file_id}"),
                expect=lambda payload, row, response: row.get("deleted") is True,
            )
        deferred_batch = client.post(
            f"{base_url}/v1/batches",
            json={
                "input_file_id": batch_input_file_id,
                "endpoint": "/v1/moderations",
                "completion_window": "24h",
                "metadata": {"local_defer": "true"},
            },
        )
        self.record(
            "batches_cancel_create",
            deferred_batch,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and row.get("resource_status") == "in_progress",
        )
        deferred_batch_id = self.json_value(deferred_batch, "id")
        self.record(
            "batches_cancel",
            client.post(f"{base_url}/v1/batches/{deferred_batch_id}/cancel"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == deferred_batch_id
            and row.get("resource_status") == "cancelled",
        )
        self.record(
            "batch_input_file_delete",
            client.delete(f"{base_url}/v1/files/{batch_input_file_id}"),
            expect=lambda payload, row, response: row.get("deleted") is True,
        )

        with self.tiny_wav().open("rb") as fh:
            self.record(
                "audio_transcriptions",
                client.post(
                    f"{base_url}/v1/audio/transcriptions",
                    files={
                        "file": ("tiny_silence.wav", fh, "audio/wav"),
                        "model": (None, "gpt-4o-mini-transcribe"),
                    },
                ),
            )

        store = client.post(f"{base_url}/v1/vector_stores", json={"name": "proxy-smoke"})
        self.record("vector_stores_create", store)
        store_id = self.json_value(store, "id")
        self.record("vector_stores_list", client.get(f"{base_url}/v1/vector_stores"))
        self.record(
            "vector_stores_retrieve_empty",
            client.get(f"{base_url}/v1/vector_stores/{store_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == store_id
            and row.get("file_counts_total") == 0,
        )
        self.record(
            "vector_stores_add_text",
            client.post(
                f"{base_url}/v1/vector_stores/{store_id}/items",
                json={
                    "text": "OAuth embeddings power local vector search.",
                    "metadata": {"source": "proxy-smoke"},
                },
            ),
        )
        vector_file = client.post(
            f"{base_url}/v1/vector_stores/{store_id}/files",
            json={"file_id": file_id, "attributes": {"source": "proxy-smoke"}},
        )
        self.record(
            "vector_store_files_create",
            vector_file,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == file_id
            and payload.get("object") == "vector_store.file",
        )
        self.record(
            "vector_store_files_list",
            client.get(f"{base_url}/v1/vector_stores/{store_id}/files"),
            expect=lambda payload, row, response: row.get("data_count") == 1,
        )
        self.record(
            "vector_store_files_retrieve",
            client.get(f"{base_url}/v1/vector_stores/{store_id}/files/{file_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == file_id
            and payload.get("object") == "vector_store.file",
        )
        self.record(
            "vector_store_files_content",
            client.get(f"{base_url}/v1/vector_stores/{store_id}/files/{file_id}/content"),
            expect=lambda payload, row, response: row.get("data_count") == 1,
        )
        batch = client.post(
            f"{base_url}/v1/vector_stores/{store_id}/file_batches",
            json={"file_ids": [file_id], "attributes": {"source": "proxy-smoke-batch"}},
        )
        self.record(
            "vector_store_file_batches_create",
            batch,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("object") == "vector_store.file_batch"
            and row.get("resource_status") == "completed"
            and row.get("file_counts_total") == 1,
        )
        batch_id = self.json_value(batch, "id")
        self.record(
            "vector_store_file_batches_retrieve",
            client.get(f"{base_url}/v1/vector_stores/{store_id}/file_batches/{batch_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == batch_id
            and payload.get("object") == "vector_store.file_batch",
        )
        self.record(
            "vector_store_file_batches_files",
            client.get(f"{base_url}/v1/vector_stores/{store_id}/file_batches/{batch_id}/files"),
            expect=lambda payload, row, response: row.get("data_count") == 1,
        )
        self.record(
            "vector_store_file_batches_cancel",
            client.post(f"{base_url}/v1/vector_stores/{store_id}/file_batches/{batch_id}/cancel"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == batch_id
            and row.get("resource_status") == "cancelled",
        )
        self.record(
            "vector_stores_retrieve_after_add",
            client.get(f"{base_url}/v1/vector_stores/{store_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == store_id
            and row.get("file_counts_total") == 2,
        )
        self.record(
            "vector_stores_search",
            client.post(
                f"{base_url}/v1/vector_stores/{store_id}/search",
                json={"query": "local vector search", "limit": 1},
            ),
            expect=lambda payload, row, response: row.get("data_count") == 1,
        )
        self.record(
            "vector_store_files_delete",
            client.delete(f"{base_url}/v1/vector_stores/{store_id}/files/{file_id}"),
            expect=lambda payload, row, response: row.get("deleted") is True,
        )
        self.record(
            "vector_stores_delete",
            client.delete(f"{base_url}/v1/vector_stores/{store_id}"),
            expect=lambda payload, row, response: row.get("deleted") is True,
        )
        self.record(
            "files_delete",
            client.delete(f"{base_url}/v1/files/{file_id}"),
            expect=lambda payload, row, response: row.get("deleted") is True,
        )
        self.record(
            "local_eval",
            client.post(
                f"{base_url}/v1/local/evals/text_expectation",
                json={
                    "prompt": "Reply exactly: proxy eval ok",
                    "expected_substring": "proxy eval ok",
                },
            ),
            expect=lambda payload, row, response: row.get("passed") is True,
        )
        created_eval = client.post(
            f"{base_url}/v1/evals",
            json={
                "name": "proxy-local-eval",
                "data_source_config": {"type": "custom", "item_schema": {}},
                "testing_criteria": [{
                    "type": "string_check",
                    "name": "contains_expected",
                    "input": "{{ output }}",
                    "operation": "like",
                    "reference": "proxy eval ok",
                }],
                "metadata": {
                    "prompt": "Reply exactly: proxy eval ok",
                    "expected_substring": "proxy eval ok",
                },
            },
        )
        self.record(
            "evals_create",
            created_eval,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("object") == "eval"
            and isinstance(payload.get("id"), str),
        )
        eval_id = self.json_value(created_eval, "id")
        self.record("evals_list", client.get(f"{base_url}/v1/evals"), expect=lambda payload, row, response: row.get("data_count", 0) > 0)
        self.record(
            "evals_retrieve",
            client.get(f"{base_url}/v1/evals/{eval_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == eval_id
            and payload.get("object") == "eval",
        )
        self.record(
            "evals_update",
            client.post(f"{base_url}/v1/evals/{eval_id}", json={"name": "proxy-local-eval-updated"}),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == eval_id
            and payload.get("name") == "proxy-local-eval-updated",
        )
        created_run = client.post(
            f"{base_url}/v1/evals/{eval_id}/runs",
            json={
                "name": "proxy-local-eval-run",
                "data_source": {
                    "type": "jsonl",
                    "source": {
                        "type": "file_content",
                        "content": [{
                            "item": {
                                "prompt": "Reply exactly: proxy eval ok",
                                "expected_substring": "proxy eval ok",
                            }
                        }],
                    },
                },
            },
        )
        self.record(
            "eval_runs_create",
            created_run,
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("object") == "eval.run"
            and row.get("resource_status") == "completed"
            and row.get("result_counts_total") == 1,
        )
        run_id = self.json_value(created_run, "id")
        self.record("eval_runs_list", client.get(f"{base_url}/v1/evals/{eval_id}/runs"), expect=lambda payload, row, response: row.get("data_count") == 1)
        self.record(
            "eval_runs_retrieve",
            client.get(f"{base_url}/v1/evals/{eval_id}/runs/{run_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == run_id
            and payload.get("object") == "eval.run",
        )
        output_items = client.get(f"{base_url}/v1/evals/{eval_id}/runs/{run_id}/output_items")
        self.record("eval_output_items_list", output_items, expect=lambda payload, row, response: row.get("data_count") == 1)
        output_item_id = self.first_data_id(output_items)
        self.record(
            "eval_output_items_retrieve",
            client.get(f"{base_url}/v1/evals/{eval_id}/runs/{run_id}/output_items/{output_item_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == output_item_id
            and payload.get("object") == "eval.run.output_item"
            and row.get("resource_status") == "pass",
        )
        self.record(
            "eval_runs_cancel",
            client.post(f"{base_url}/v1/evals/{eval_id}/runs/{run_id}"),
            expect=lambda payload, row, response: isinstance(payload, dict)
            and payload.get("id") == run_id
            and row.get("resource_status") == "canceled",
        )
        self.record(
            "eval_runs_delete",
            client.delete(f"{base_url}/v1/evals/{eval_id}/runs/{run_id}"),
            expect=lambda payload, row, response: row.get("deleted") is True,
        )
        self.record(
            "evals_delete",
            client.delete(f"{base_url}/v1/evals/{eval_id}"),
            expect=lambda payload, row, response: row.get("deleted") is True,
        )
        if self.include_speech:
            self.record(
                "audio_speech",
                client.post(
                    f"{base_url}/v1/audio/speech",
                    json={"input": "oauth proxy voice ok"},
                ),
                expect_binary=True,
            )
        if write:
            self.write_reports(base_url)
        return 1 if any(row["status"] != "pass" for row in self.rows) else 0

    def write_reports(self, base_url: str) -> None:
        REPORTS.mkdir(exist_ok=True)
        finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        payload = {
            "finished_at": finished_at,
            "base_url": base_url,
            "include_speech": self.include_speech,
            "include_images": self.include_images,
            "results": self.rows,
        }
        (REPORTS / "proxy_smoke_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
        lines = [
            "# Proxy Smoke Report",
            "",
            f"- Finished: `{finished_at}`",
            f"- Base URL: `{base_url}`",
            f"- Include speech: `{self.include_speech}`",
            f"- Include images: `{self.include_images}`",
            "",
            "| Status | Test | Evidence |",
            "|---|---|---|",
        ]
        for row in self.rows:
            evidence = []
            for key in (
                "http_status",
                "content_type",
                "access_control_allow_origin",
                "access_control_allow_methods",
                "access_control_allow_headers",
                "object",
                "route",
                "data_count",
                "id_prefix",
                "resource_status",
                "output_text_len",
                "choices_count",
                "embedding_dims",
                "local_path_present",
                "bytes",
                "passed",
                "deleted",
                "file_counts_total",
                "file_id_prefix",
                "part_count",
                "output_file_id_prefix",
                "request_counts_total",
                "results_count",
                "flagged",
                "result_counts_total",
                "error_type",
                "validator_error",
                "sse_events",
                "done_present",
            ):
                value = row.get(key)
                if value is not None:
                    evidence.append(f"{key}={value}")
            lines.append(f"| `{row['status']}` | `{row['name']}` | {'; '.join(evidence)} |")
        lines.append("")
        (REPORTS / "proxy_smoke_latest.md").write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the local OAuth compatibility proxy and smoke-test common /v1 routes.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="Use 0 for an ephemeral port.")
    parser.add_argument("--skip-speech", action="store_true", help="Skip the Realtime PCM16 speech route.")
    parser.add_argument("--include-images", action="store_true", help="Also run the Codex image-generation proxy route.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/proxy_smoke_latest.*.")
    args = parser.parse_args()

    try:
        server = make_server(args.host, args.port)
    except PermissionError as exc:
        print(
            f"Cannot start local proxy on {args.host}:{args.port}: {exc}. "
            "This environment appears to block localhost socket binding.",
            flush=True,
        )
        return 2
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        return ProxySmoke(include_speech=not args.skip_speech, include_images=args.include_images).run(
            f"http://{args.host}:{port}",
            write=not args.no_write,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
