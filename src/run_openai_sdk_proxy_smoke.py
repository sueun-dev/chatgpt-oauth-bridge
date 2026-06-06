from __future__ import annotations

import argparse
import json
import threading
import time
import wave
from pathlib import Path
from typing import Any, Callable, Dict

from openai import OpenAI

from oauth_feature_router import ROOT
from oauth_openai_compat_server import make_server


REPORTS = ROOT / "reports"
ARTIFACTS = ROOT / "artifacts"


class OpenAISDKProxySmoke:
    def __init__(self, *, include_speech: bool, include_images: bool) -> None:
        self.include_speech = include_speech
        self.include_images = include_images
        self.rows: list[Dict[str, Any]] = []

    def record(self, name: str, fn: Callable[[], Dict[str, Any]], *, expect: Callable[[Dict[str, Any]], bool]) -> Dict[str, Any]:
        try:
            row = {**fn(), "name": name}
            row["status"] = "pass" if expect(row) else "fail"
        except Exception as exc:
            row = {
                "name": name,
                "status": "fail",
                "error_type": type(exc).__name__,
                "error": str(exc)[:600],
            }
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

    def upload_probe(self) -> Path:
        path = ARTIFACTS / "sdk_proxy_upload_probe.txt"
        ARTIFACTS.mkdir(exist_ok=True)
        path.write_text("OpenAI SDK proxy upload probe. No secrets.\n")
        return path

    def batch_input_probe(self) -> Path:
        path = ARTIFACTS / "sdk_proxy_batch_input.jsonl"
        ARTIFACTS.mkdir(exist_ok=True)
        path.write_text(json.dumps({
            "custom_id": "sdk-moderation-1",
            "method": "POST",
            "url": "/v1/moderations",
            "body": {"input": "hello from sdk batch moderation"},
        }) + "\n")
        return path

    def _raw_get(self, client: OpenAI, path: str) -> Dict[str, Any]:
        return self._as_dict(client.get(path, cast_to=Dict[str, Any]))

    def _raw_post(self, client: OpenAI, path: str, body: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return self._as_dict(client.post(path, cast_to=Dict[str, Any], body=body or {}))

    def _raw_delete(self, client: OpenAI, path: str) -> Dict[str, Any]:
        return self._as_dict(client.delete(path, cast_to=Dict[str, Any]))

    def _as_dict(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump()
            if isinstance(dumped, dict):
                return dumped
        return dict(value)

    def run(self, sdk_base_url: str, *, write: bool = True) -> int:
        client = OpenAI(api_key="oauth-local-proxy", base_url=sdk_base_url, timeout=120)

        self.record(
            "sdk_models_list",
            lambda: self._models_row(client),
            expect=lambda row: row.get("object") == "list" and int(row.get("data_count", 0)) > 0,
        )
        self.record(
            "sdk_models_retrieve",
            lambda: self._models_retrieve_row(client),
            expect=lambda row: bool(row.get("id")) and row.get("object") == "model",
        )

        assistant_row = self.record(
            "sdk_assistants_create",
            lambda: self._assistants_create_row(client),
            expect=lambda row: str(row.get("id", "")).startswith("asst_local_")
            and row.get("object") == "assistant",
        )
        assistant_id = str(assistant_row.get("id") or "")
        self.record(
            "sdk_assistants_list",
            lambda: self._assistants_list_row(client),
            expect=lambda row: int(row.get("data_count", 0)) > 0,
        )
        self.record(
            "sdk_assistants_retrieve",
            lambda: self._assistants_retrieve_row(client, assistant_id),
            expect=lambda row: row.get("id") == assistant_id and row.get("object") == "assistant",
        )
        self.record(
            "sdk_assistants_update",
            lambda: self._assistants_update_row(client, assistant_id),
            expect=lambda row: row.get("id") == assistant_id and row.get("resource_name") == "sdk-local-assistant-updated",
        )
        thread_row = self.record(
            "sdk_threads_create",
            lambda: self._threads_create_row(client),
            expect=lambda row: str(row.get("id", "")).startswith("thread_local_")
            and row.get("object") == "thread",
        )
        thread_id = str(thread_row.get("id") or "")
        self.record(
            "sdk_threads_retrieve",
            lambda: self._threads_retrieve_row(client, thread_id),
            expect=lambda row: row.get("id") == thread_id and row.get("object") == "thread",
        )
        self.record(
            "sdk_threads_update",
            lambda: self._threads_update_row(client, thread_id),
            expect=lambda row: row.get("id") == thread_id,
        )
        message_row = self.record(
            "sdk_thread_messages_create",
            lambda: self._thread_messages_create_row(client, thread_id),
            expect=lambda row: str(row.get("id", "")).startswith("msg_local_")
            and row.get("object") == "thread.message",
        )
        message_id = str(message_row.get("id") or "")
        self.record(
            "sdk_thread_messages_list",
            lambda: self._thread_messages_list_row(client, thread_id),
            expect=lambda row: int(row.get("data_count", 0)) >= 1,
        )
        self.record(
            "sdk_thread_messages_retrieve",
            lambda: self._thread_messages_retrieve_row(client, thread_id, message_id),
            expect=lambda row: row.get("id") == message_id and row.get("object") == "thread.message",
        )
        self.record(
            "sdk_thread_messages_update",
            lambda: self._thread_messages_update_row(client, thread_id, message_id),
            expect=lambda row: row.get("id") == message_id,
        )
        run_row = self.record(
            "sdk_thread_runs_create",
            lambda: self._thread_runs_create_row(client, thread_id, assistant_id),
            expect=lambda row: str(row.get("id", "")).startswith("run_local_")
            and row.get("object") == "thread.run"
            and row.get("resource_status") == "completed",
        )
        run_id = str(run_row.get("id") or "")
        self.record(
            "sdk_thread_runs_list",
            lambda: self._thread_runs_list_row(client, thread_id),
            expect=lambda row: int(row.get("data_count", 0)) >= 1,
        )
        self.record(
            "sdk_thread_runs_retrieve",
            lambda: self._thread_runs_retrieve_row(client, thread_id, run_id),
            expect=lambda row: row.get("id") == run_id and row.get("object") == "thread.run",
        )
        self.record(
            "sdk_thread_runs_update",
            lambda: self._thread_runs_update_row(client, thread_id, run_id),
            expect=lambda row: row.get("id") == run_id,
        )
        steps_row = self.record(
            "sdk_thread_run_steps_list",
            lambda: self._thread_run_steps_list_row(client, thread_id, run_id),
            expect=lambda row: int(row.get("data_count", 0)) == 1 and bool(row.get("first_id")),
        )
        step_id = str(steps_row.get("first_id") or "")
        self.record(
            "sdk_thread_run_steps_retrieve",
            lambda: self._thread_run_steps_retrieve_row(client, thread_id, run_id, step_id),
            expect=lambda row: row.get("id") == step_id and row.get("object") == "thread.run.step",
        )
        self.record(
            "sdk_thread_runs_cancel",
            lambda: self._thread_runs_cancel_row(client, thread_id, run_id),
            expect=lambda row: row.get("id") == run_id and row.get("resource_status") == "cancelled",
        )
        self.record(
            "sdk_threads_create_and_run",
            lambda: self._threads_create_and_run_row(client, assistant_id),
            expect=lambda row: str(row.get("id", "")).startswith("run_local_")
            and row.get("resource_status") == "completed",
        )
        self.record(
            "sdk_thread_messages_delete",
            lambda: self._thread_messages_delete_row(client, thread_id, message_id),
            expect=lambda row: row.get("deleted") is True,
        )
        self.record(
            "sdk_threads_delete",
            lambda: self._threads_delete_row(client, thread_id),
            expect=lambda row: row.get("deleted") is True,
        )
        self.record(
            "sdk_assistants_delete",
            lambda: self._assistants_delete_row(client, assistant_id),
            expect=lambda row: row.get("deleted") is True,
        )

        response_row = self.record(
            "sdk_responses_create",
            lambda: self._responses_row(client),
            expect=lambda row: int(row.get("output_text_len", 0)) > 0 and int(row.get("output_count", 0)) > 0,
        )
        response_id = str(response_row.get("id") or "")
        self.record(
            "sdk_responses_retrieve",
            lambda: self._responses_retrieve_row(client, response_id),
            expect=lambda row: row.get("id") == response_id
            and int(row.get("output_text_len", 0)) > 0,
        )
        self.record(
            "sdk_response_input_items_list",
            lambda: self._response_input_items_row(client, response_id),
            expect=lambda row: int(row.get("data_count", 0)) == 1,
        )
        self.record(
            "sdk_responses_cancel",
            lambda: self._responses_cancel_row(client, response_id),
            expect=lambda row: row.get("id") == response_id
            and row.get("resource_status") == "cancelled",
        )
        self.record(
            "sdk_responses_delete",
            lambda: self._responses_delete_row(client, response_id),
            expect=lambda row: row.get("deleted_none") is True,
        )
        self.record(
            "sdk_responses_stream",
            lambda: self._responses_stream_row(client),
            expect=lambda row: int(row.get("delta_text_len", 0)) > 0 and row.get("completed") is True,
        )
        self.record(
            "sdk_responses_compact",
            lambda: self._responses_compact_row(client),
            expect=lambda row: row.get("object") == "response.compaction"
            and int(row.get("output_count", 0)) == 1
            and int(row.get("total_tokens", 0)) > 0,
        )

        self.record(
            "sdk_completions_create",
            lambda: self._completions_row(client),
            expect=lambda row: int(row.get("choices_count", 0)) == 1 and int(row.get("text_len", 0)) > 0,
        )
        self.record(
            "sdk_completions_stream",
            lambda: self._completions_stream_row(client),
            expect=lambda row: int(row.get("delta_text_len", 0)) > 0,
        )

        chat_row = self.record(
            "sdk_chat_completions_create",
            lambda: self._chat_row(client),
            expect=lambda row: int(row.get("choices_count", 0)) == 1 and int(row.get("message_len", 0)) > 0,
        )
        chat_id = str(chat_row.get("id") or "")
        self.record(
            "sdk_chat_completions_retrieve",
            lambda: self._chat_retrieve_row(client, chat_id),
            expect=lambda row: row.get("id") == chat_id
            and int(row.get("choices_count", 0)) == 1,
        )
        self.record(
            "sdk_chat_completions_list",
            lambda: self._chat_list_row(client),
            expect=lambda row: int(row.get("data_count", 0)) > 0,
        )
        self.record(
            "sdk_chat_completions_update",
            lambda: self._chat_update_row(client, chat_id),
            expect=lambda row: row.get("id") == chat_id,
        )
        self.record(
            "sdk_chat_completion_messages",
            lambda: self._chat_messages_row(client, chat_id),
            expect=lambda row: int(row.get("data_count", 0)) == 1
            and row.get("first_role") == "assistant",
        )
        self.record(
            "sdk_chat_completions_delete",
            lambda: self._chat_delete_row(client, chat_id),
            expect=lambda row: row.get("id") == chat_id
            and row.get("deleted") is True,
        )
        self.record(
            "sdk_chat_completions_stream",
            lambda: self._chat_stream_row(client),
            expect=lambda row: int(row.get("delta_text_len", 0)) > 0,
        )

        self.record(
            "sdk_embeddings_create",
            lambda: self._embeddings_row(client),
            expect=lambda row: int(row.get("embedding_dims", 0)) > 100,
        )

        self.record(
            "sdk_moderations_create",
            lambda: self._moderations_row(client),
            expect=lambda row: int(row.get("results_count", 0)) == 1
            and row.get("flagged") is False,
        )
        batch_input_row = self.record(
            "sdk_batch_input_file_create",
            lambda: self._batch_input_file_create_row(client),
            expect=lambda row: bool(row.get("id")) and row.get("object") == "file",
        )
        batch_input_file_id = str(batch_input_row.get("id") or "")
        batch_row = self.record(
            "sdk_batches_create",
            lambda: self._batches_create_row(client, batch_input_file_id),
            expect=lambda row: str(row.get("id", "")).startswith("batch-local-")
            and row.get("object") == "batch"
            and row.get("resource_status") == "completed"
            and int(row.get("request_counts_total", 0)) == 1
            and bool(row.get("output_file_id")),
        )
        batch_id = str(batch_row.get("id") or "")
        batch_output_file_id = str(batch_row.get("output_file_id") or "")
        self.record(
            "sdk_batches_list",
            lambda: self._batches_list_row(client),
            expect=lambda row: int(row.get("data_count", 0)) > 0,
        )
        self.record(
            "sdk_batches_retrieve",
            lambda: self._batches_retrieve_row(client, batch_id),
            expect=lambda row: row.get("id") == batch_id and row.get("object") == "batch",
        )
        if batch_output_file_id:
            self.record(
                "sdk_batches_output_file_content",
                lambda: self._files_content_row(client, batch_output_file_id),
                expect=lambda row: int(row.get("bytes", 0)) > 10,
            )
            self.record(
                "sdk_batches_output_file_delete",
                lambda: self._files_delete_row(client, batch_output_file_id),
                expect=lambda row: row.get("deleted") is True,
            )
        deferred_batch_row = self.record(
            "sdk_batches_cancel_create",
            lambda: self._batches_create_row(client, batch_input_file_id, metadata={"local_defer": "true"}),
            expect=lambda row: str(row.get("id", "")).startswith("batch-local-")
            and row.get("resource_status") == "in_progress",
        )
        deferred_batch_id = str(deferred_batch_row.get("id") or "")
        self.record(
            "sdk_batches_cancel",
            lambda: self._batches_cancel_row(client, deferred_batch_id),
            expect=lambda row: row.get("id") == deferred_batch_id
            and row.get("resource_status") == "cancelled",
        )
        self.record(
            "sdk_batch_input_file_delete",
            lambda: self._files_delete_row(client, batch_input_file_id),
            expect=lambda row: row.get("deleted") is True,
        )

        upload_row = self.record(
            "sdk_uploads_create",
            lambda: self._uploads_create_row(client),
            expect=lambda row: str(row.get("id", "")).startswith("upload-local-")
            and row.get("object") == "upload"
            and row.get("resource_status") == "pending",
        )
        upload_id = str(upload_row.get("id") or "")
        upload_part_row = self.record(
            "sdk_upload_parts_create",
            lambda: self._upload_parts_create_row(client, upload_id),
            expect=lambda row: str(row.get("id", "")).startswith("uploadpart-local-")
            and row.get("object") == "upload.part"
            and row.get("upload_id") == upload_id,
        )
        upload_part_id = str(upload_part_row.get("id") or "")
        upload_complete_row = self.record(
            "sdk_uploads_complete",
            lambda: self._uploads_complete_row(client, upload_id, upload_part_id),
            expect=lambda row: row.get("id") == upload_id
            and row.get("object") == "upload"
            and row.get("resource_status") == "completed"
            and str(row.get("file_id", "")).startswith("file_"),
        )
        completed_upload_file_id = str(upload_complete_row.get("file_id") or "")
        if completed_upload_file_id:
            self.record(
                "sdk_uploads_completed_file_delete",
                lambda: self._files_delete_row(client, completed_upload_file_id),
                expect=lambda row: row.get("deleted") is True,
            )
        cancel_upload_row = self.record(
            "sdk_uploads_cancel_create",
            lambda: self._uploads_create_row(client),
            expect=lambda row: str(row.get("id", "")).startswith("upload-local-")
            and row.get("resource_status") == "pending",
        )
        cancel_upload_id = str(cancel_upload_row.get("id") or "")
        self.record(
            "sdk_uploads_cancel",
            lambda: self._uploads_cancel_row(client, cancel_upload_id),
            expect=lambda row: row.get("id") == cancel_upload_id
            and row.get("resource_status") == "cancelled",
        )

        eval_row = self.record(
            "sdk_evals_create",
            lambda: self._evals_create_row(client),
            expect=lambda row: str(row.get("id", "")).startswith("eval-local-")
            and row.get("object") == "eval",
        )
        eval_id = str(eval_row.get("id") or "")
        self.record(
            "sdk_evals_list",
            lambda: self._evals_list_row(client),
            expect=lambda row: int(row.get("data_count", 0)) > 0,
        )
        self.record(
            "sdk_evals_retrieve",
            lambda: self._evals_retrieve_row(client, eval_id),
            expect=lambda row: row.get("id") == eval_id and row.get("object") == "eval",
        )
        self.record(
            "sdk_evals_update",
            lambda: self._evals_update_row(client, eval_id),
            expect=lambda row: row.get("id") == eval_id and row.get("resource_name") == "sdk-local-eval-updated",
        )
        eval_run_row = self.record(
            "sdk_eval_runs_create",
            lambda: self._eval_runs_create_row(client, eval_id),
            expect=lambda row: str(row.get("id", "")).startswith("evalrun-local-")
            and row.get("object") == "eval.run"
            and row.get("resource_status") == "completed"
            and int(row.get("result_counts_total", 0)) == 1,
        )
        eval_run_id = str(eval_run_row.get("id") or "")
        self.record(
            "sdk_eval_runs_list",
            lambda: self._eval_runs_list_row(client, eval_id),
            expect=lambda row: int(row.get("data_count", 0)) == 1,
        )
        self.record(
            "sdk_eval_runs_retrieve",
            lambda: self._eval_runs_retrieve_row(client, eval_id, eval_run_id),
            expect=lambda row: row.get("id") == eval_run_id and row.get("object") == "eval.run",
        )
        eval_output_items_row = self.record(
            "sdk_eval_output_items_list",
            lambda: self._eval_output_items_list_row(client, eval_id, eval_run_id),
            expect=lambda row: int(row.get("data_count", 0)) == 1 and bool(row.get("first_id")),
        )
        eval_output_item_id = str(eval_output_items_row.get("first_id") or "")
        self.record(
            "sdk_eval_output_items_retrieve",
            lambda: self._eval_output_items_retrieve_row(client, eval_id, eval_run_id, eval_output_item_id),
            expect=lambda row: row.get("id") == eval_output_item_id
            and row.get("object") == "eval.run.output_item"
            and row.get("resource_status") == "pass",
        )
        self.record(
            "sdk_eval_runs_cancel",
            lambda: self._eval_runs_cancel_row(client, eval_id, eval_run_id),
            expect=lambda row: row.get("id") == eval_run_id and row.get("resource_status") == "canceled",
        )
        self.record(
            "sdk_eval_runs_delete",
            lambda: self._eval_runs_delete_row(client, eval_id, eval_run_id),
            expect=lambda row: row.get("deleted") is True,
        )
        self.record(
            "sdk_evals_delete",
            lambda: self._evals_delete_row(client, eval_id),
            expect=lambda row: row.get("deleted") is True,
        )

        file_row = self.record(
            "sdk_files_create",
            lambda: self._files_create_row(client),
            expect=lambda row: str(row.get("id", "")).startswith("file_") and row.get("object") == "file",
        )
        file_id = str(file_row.get("id") or "")
        self.record(
            "sdk_files_retrieve",
            lambda: self._files_retrieve_row(client, file_id),
            expect=lambda row: row.get("id") == file_id and row.get("object") == "file",
        )
        self.record(
            "sdk_files_content",
            lambda: self._files_content_row(client, file_id),
            expect=lambda row: int(row.get("bytes", 0)) > 0,
        )

        self.record(
            "sdk_files_list",
            lambda: self._files_list_row(client),
            expect=lambda row: int(row.get("data_count", 0)) > 0,
        )

        vector_row = self.record(
            "sdk_vector_stores_create",
            lambda: self._vector_stores_create_row(client),
            expect=lambda row: str(row.get("id", "")).startswith("vs-local-") and row.get("object") == "vector_store",
        )
        store_id = str(vector_row.get("id") or "")
        self.record(
            "sdk_vector_store_files_create",
            lambda: self._vector_store_files_create_row(client, store_id, file_id),
            expect=lambda row: row.get("id") == file_id and row.get("object") == "vector_store.file",
        )
        self.record(
            "sdk_vector_store_files_list",
            lambda: self._vector_store_files_list_row(client, store_id),
            expect=lambda row: int(row.get("data_count", 0)) == 1,
        )
        self.record(
            "sdk_vector_store_files_retrieve",
            lambda: self._vector_store_files_retrieve_row(client, store_id, file_id),
            expect=lambda row: row.get("id") == file_id and row.get("object") == "vector_store.file",
        )
        self.record(
            "sdk_vector_store_files_content",
            lambda: self._vector_store_files_content_row(client, store_id, file_id),
            expect=lambda row: int(row.get("data_count", 0)) == 1,
        )
        batch_row = self.record(
            "sdk_vector_store_file_batches_create",
            lambda: self._vector_store_file_batches_create_row(client, store_id, file_id),
            expect=lambda row: str(row.get("id", "")).startswith("vsfb-local-")
            and row.get("object") == "vector_store.file_batch"
            and row.get("resource_status") == "completed"
            and int(row.get("file_counts_total", 0)) == 1,
        )
        batch_id = str(batch_row.get("id") or "")
        self.record(
            "sdk_vector_store_file_batches_retrieve",
            lambda: self._vector_store_file_batches_retrieve_row(client, store_id, batch_id),
            expect=lambda row: row.get("id") == batch_id
            and row.get("object") == "vector_store.file_batch",
        )
        self.record(
            "sdk_vector_store_file_batches_files",
            lambda: self._vector_store_file_batches_files_row(client, store_id, batch_id),
            expect=lambda row: int(row.get("data_count", 0)) == 1,
        )
        self.record(
            "sdk_vector_store_file_batches_cancel",
            lambda: self._vector_store_file_batches_cancel_row(client, store_id, batch_id),
            expect=lambda row: row.get("id") == batch_id
            and row.get("resource_status") == "cancelled",
        )
        self.record(
            "sdk_vector_stores_list",
            lambda: self._vector_stores_list_row(client),
            expect=lambda row: int(row.get("data_count", 0)) > 0,
        )
        self.record(
            "sdk_vector_stores_retrieve",
            lambda: self._vector_stores_retrieve_row(client, store_id),
            expect=lambda row: row.get("id") == store_id and row.get("object") == "vector_store",
        )
        self.record(
            "sdk_vector_store_files_delete",
            lambda: self._vector_store_files_delete_row(client, store_id, file_id),
            expect=lambda row: row.get("deleted") is True,
        )
        self.record(
            "sdk_files_delete",
            lambda: self._files_delete_row(client, file_id),
            expect=lambda row: row.get("deleted") is True,
        )
        self.record(
            "sdk_vector_stores_delete",
            lambda: self._vector_stores_delete_row(client, store_id),
            expect=lambda row: row.get("deleted") is True,
        )

        self.record(
            "sdk_audio_transcriptions_create",
            lambda: self._transcription_row(client),
            expect=lambda row: row.get("text_present") is True,
        )

        if self.include_speech:
            self.record(
                "sdk_audio_speech_create",
                lambda: self._speech_row(client),
                expect=lambda row: int(row.get("bytes", 0)) > 100,
            )

        if self.include_images:
            self.record(
                "sdk_images_generate",
                lambda: self._image_row(client),
                expect=lambda row: int(row.get("data_count", 0)) == 1
                and (row.get("b64_json_present") is True or row.get("url_present") is True),
            )

        if write:
            self.write_reports(sdk_base_url)
        return 1 if any(row["status"] != "pass" for row in self.rows) else 0

    def _responses_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.responses.create(model="gpt-5.5", input="Reply exactly: sdk responses ok")
        output_text = getattr(response, "output_text", "") or ""
        output = getattr(response, "output", None) or []
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "output_text_len": len(output_text),
            "output_count": len(output),
        }

    def _responses_retrieve_row(self, client: OpenAI, response_id: str) -> Dict[str, Any]:
        response = client.responses.retrieve(response_id)
        output_text = getattr(response, "output_text", "") or ""
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "resource_status": getattr(response, "status", None),
            "output_text_len": len(output_text),
        }

    def _response_input_items_row(self, client: OpenAI, response_id: str) -> Dict[str, Any]:
        response = client.responses.input_items.list(response_id)
        return {
            "object": response.object,
            "data_count": len(response.data),
            "first_type": getattr(response.data[0], "type", None) if response.data else None,
        }

    def _responses_cancel_row(self, client: OpenAI, response_id: str) -> Dict[str, Any]:
        response = client.responses.cancel(response_id)
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "resource_status": getattr(response, "status", None),
        }

    def _responses_delete_row(self, client: OpenAI, response_id: str) -> Dict[str, Any]:
        response = client.responses.delete(response_id)
        return {"deleted_none": response is None}

    def _responses_stream_row(self, client: OpenAI) -> Dict[str, Any]:
        text = ""
        event_types = []
        for event in client.responses.create(model="gpt-5.5", input="Reply exactly: sdk responses stream ok", stream=True):
            event_types.append(event.type)
            if event.type == "response.output_text.delta":
                text += event.delta
        return {
            "event_count": len(event_types),
            "delta_text_len": len(text),
            "completed": "response.completed" in event_types,
        }

    def _responses_compact_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.responses.compact(
            model="gpt-5.5",
            input="Compact this SDK prompt and preserve compact-ok.",
        )
        return {
            "object": response.object,
            "id": response.id,
            "output_count": len(response.output or []),
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }

    def _models_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.models.list()
        return {
            "object": response.object,
            "data_count": len(response.data),
            "first_model": response.data[0].id if response.data else None,
        }

    def _models_retrieve_row(self, client: OpenAI) -> Dict[str, Any]:
        first_model = client.models.list().data[0].id
        response = client.models.retrieve(first_model)
        return {
            "object": response.object,
            "id": response.id,
        }

    def _assistants_create_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.beta.assistants.create(
            model="gpt-5.5",
            name="sdk-local-assistant",
            instructions="Reply briefly.",
        )
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "resource_name": getattr(response, "name", None),
            "model": getattr(response, "model", None),
        }

    def _assistants_list_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.beta.assistants.list()
        return {
            "object": getattr(response, "object", None),
            "data_count": len(response.data),
            "first_id": response.data[0].id if response.data else None,
        }

    def _assistants_retrieve_row(self, client: OpenAI, assistant_id: str) -> Dict[str, Any]:
        response = client.beta.assistants.retrieve(assistant_id)
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "resource_name": getattr(response, "name", None),
        }

    def _assistants_update_row(self, client: OpenAI, assistant_id: str) -> Dict[str, Any]:
        response = client.beta.assistants.update(assistant_id, name="sdk-local-assistant-updated")
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "resource_name": getattr(response, "name", None),
        }

    def _assistants_delete_row(self, client: OpenAI, assistant_id: str) -> Dict[str, Any]:
        response = client.beta.assistants.delete(assistant_id)
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", assistant_id),
            "deleted": bool(getattr(response, "deleted", False)),
        }

    def _threads_create_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.beta.threads.create(
            messages=[{"role": "user", "content": "Reply exactly: sdk assistant thread ok"}],
            metadata={"source": "sdk-smoke"},
        )
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
        }

    def _threads_retrieve_row(self, client: OpenAI, thread_id: str) -> Dict[str, Any]:
        response = client.beta.threads.retrieve(thread_id)
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
        }

    def _threads_update_row(self, client: OpenAI, thread_id: str) -> Dict[str, Any]:
        response = client.beta.threads.update(thread_id, metadata={"source": "sdk-smoke-updated"})
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
        }

    def _threads_delete_row(self, client: OpenAI, thread_id: str) -> Dict[str, Any]:
        response = client.beta.threads.delete(thread_id)
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", thread_id),
            "deleted": bool(getattr(response, "deleted", False)),
        }

    def _thread_messages_create_row(self, client: OpenAI, thread_id: str) -> Dict[str, Any]:
        response = client.beta.threads.messages.create(
            thread_id,
            role="user",
            content="Reply exactly: sdk assistant message ok",
        )
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "role": getattr(response, "role", None),
            "thread_id": getattr(response, "thread_id", None),
        }

    def _thread_messages_list_row(self, client: OpenAI, thread_id: str) -> Dict[str, Any]:
        response = client.beta.threads.messages.list(thread_id)
        return {
            "object": getattr(response, "object", None),
            "data_count": len(response.data),
            "first_id": response.data[0].id if response.data else None,
        }

    def _thread_messages_retrieve_row(self, client: OpenAI, thread_id: str, message_id: str) -> Dict[str, Any]:
        response = client.beta.threads.messages.retrieve(message_id, thread_id=thread_id)
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "role": getattr(response, "role", None),
        }

    def _thread_messages_update_row(self, client: OpenAI, thread_id: str, message_id: str) -> Dict[str, Any]:
        response = client.beta.threads.messages.update(
            message_id,
            thread_id=thread_id,
            metadata={"source": "sdk-smoke-updated"},
        )
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
        }

    def _thread_messages_delete_row(self, client: OpenAI, thread_id: str, message_id: str) -> Dict[str, Any]:
        response = client.beta.threads.messages.delete(message_id, thread_id=thread_id)
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", message_id),
            "deleted": bool(getattr(response, "deleted", False)),
        }

    def _thread_runs_create_row(self, client: OpenAI, thread_id: str, assistant_id: str) -> Dict[str, Any]:
        response = client.beta.threads.runs.create(thread_id, assistant_id=assistant_id)
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "assistant_id": getattr(response, "assistant_id", None),
            "thread_id": getattr(response, "thread_id", None),
            "resource_status": getattr(response, "status", None),
        }

    def _thread_runs_list_row(self, client: OpenAI, thread_id: str) -> Dict[str, Any]:
        response = client.beta.threads.runs.list(thread_id)
        return {
            "object": getattr(response, "object", None),
            "data_count": len(response.data),
            "first_id": response.data[0].id if response.data else None,
        }

    def _thread_runs_retrieve_row(self, client: OpenAI, thread_id: str, run_id: str) -> Dict[str, Any]:
        response = client.beta.threads.runs.retrieve(run_id, thread_id=thread_id)
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "resource_status": getattr(response, "status", None),
        }

    def _thread_runs_update_row(self, client: OpenAI, thread_id: str, run_id: str) -> Dict[str, Any]:
        response = client.beta.threads.runs.update(run_id, thread_id=thread_id, metadata={"source": "sdk-smoke"})
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "resource_status": getattr(response, "status", None),
        }

    def _thread_runs_cancel_row(self, client: OpenAI, thread_id: str, run_id: str) -> Dict[str, Any]:
        response = client.beta.threads.runs.cancel(run_id, thread_id=thread_id)
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "resource_status": getattr(response, "status", None),
        }

    def _thread_run_steps_list_row(self, client: OpenAI, thread_id: str, run_id: str) -> Dict[str, Any]:
        response = client.beta.threads.runs.steps.list(run_id, thread_id=thread_id)
        return {
            "object": getattr(response, "object", None),
            "data_count": len(response.data),
            "first_id": response.data[0].id if response.data else None,
            "first_type": getattr(response.data[0], "type", None) if response.data else None,
        }

    def _thread_run_steps_retrieve_row(self, client: OpenAI, thread_id: str, run_id: str, step_id: str) -> Dict[str, Any]:
        response = client.beta.threads.runs.steps.retrieve(step_id, thread_id=thread_id, run_id=run_id)
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "resource_status": getattr(response, "status", None),
            "step_type": getattr(response, "type", None),
        }

    def _threads_create_and_run_row(self, client: OpenAI, assistant_id: str) -> Dict[str, Any]:
        response = client.beta.threads.create_and_run(
            assistant_id=assistant_id,
            thread={"messages": [{"role": "user", "content": "Reply exactly: sdk create and run ok"}]},
        )
        return {
            "object": getattr(response, "object", None),
            "id": getattr(response, "id", None),
            "assistant_id": getattr(response, "assistant_id", None),
            "thread_id": getattr(response, "thread_id", None),
            "resource_status": getattr(response, "status", None),
        }

    def _chat_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.chat.completions.create(
            model="gpt-5.5",
            messages=[{"role": "user", "content": "Reply exactly: sdk chat ok"}],
        )
        choices = response.choices or []
        message = choices[0].message.content if choices else ""
        return {
            "object": response.object,
            "id": response.id,
            "choices_count": len(choices),
            "message_len": len(message or ""),
        }

    def _chat_retrieve_row(self, client: OpenAI, chat_id: str) -> Dict[str, Any]:
        response = client.chat.completions.retrieve(chat_id)
        return {
            "object": response.object,
            "id": response.id,
            "choices_count": len(response.choices or []),
        }

    def _chat_list_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.chat.completions.list()
        return {
            "object": response.object,
            "data_count": len(response.data),
        }

    def _chat_update_row(self, client: OpenAI, chat_id: str) -> Dict[str, Any]:
        response = client.chat.completions.update(chat_id, metadata={"source": "sdk-smoke"})
        return {
            "object": response.object,
            "id": response.id,
        }

    def _chat_messages_row(self, client: OpenAI, chat_id: str) -> Dict[str, Any]:
        response = client.chat.completions.messages.list(chat_id)
        return {
            "object": response.object,
            "data_count": len(response.data),
            "first_role": response.data[0].role if response.data else None,
        }

    def _chat_delete_row(self, client: OpenAI, chat_id: str) -> Dict[str, Any]:
        response = client.chat.completions.delete(chat_id)
        return {
            "object": response.object,
            "id": response.id,
            "deleted": bool(response.deleted),
        }

    def _chat_stream_row(self, client: OpenAI) -> Dict[str, Any]:
        text = ""
        chunks = 0
        for chunk in client.chat.completions.create(
            model="gpt-5.5",
            messages=[{"role": "user", "content": "Reply exactly: sdk stream chat ok"}],
            stream=True,
        ):
            chunks += 1
            text += chunk.choices[0].delta.content or ""
        return {
            "chunk_count": chunks,
            "delta_text_len": len(text),
        }

    def _completions_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.completions.create(
            model="gpt-5.5",
            prompt="Reply exactly: sdk legacy completion ok",
        )
        choices = response.choices or []
        text = choices[0].text if choices else ""
        return {
            "object": response.object,
            "id": response.id,
            "choices_count": len(choices),
            "text_len": len(text or ""),
        }

    def _completions_stream_row(self, client: OpenAI) -> Dict[str, Any]:
        text = ""
        chunks = 0
        for chunk in client.completions.create(
            model="gpt-5.5",
            prompt="Reply exactly: sdk legacy completion stream ok",
            stream=True,
        ):
            chunks += 1
            choices = chunk.choices or []
            text += choices[0].text or "" if choices else ""
        return {
            "chunk_count": chunks,
            "delta_text_len": len(text),
        }

    def _embeddings_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.embeddings.create(model="text-embedding-3-small", input="sdk embedding")
        return {
            "object": response.object,
            "data_count": len(response.data),
            "embedding_dims": len(response.data[0].embedding) if response.data else 0,
        }

    def _moderations_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.moderations.create(input="hello from sdk moderation")
        first = response.results[0] if response.results else None
        return {
            "id": response.id,
            "model": response.model,
            "results_count": len(response.results),
            "flagged": bool(first.flagged) if first else None,
        }

    def _batch_input_file_create_row(self, client: OpenAI) -> Dict[str, Any]:
        with self.batch_input_probe().open("rb") as fh:
            response = client.files.create(file=fh, purpose="batch")
        return {
            "object": response.object,
            "id": response.id,
            "filename": response.filename,
            "bytes": response.bytes,
        }

    def _batches_create_row(self, client: OpenAI, input_file_id: str, metadata: Dict[str, str] | None = None) -> Dict[str, Any]:
        response = client.batches.create(
            input_file_id=input_file_id,
            endpoint="/v1/moderations",
            completion_window="24h",
            metadata=metadata,
        )
        return {
            "object": response.object,
            "id": response.id,
            "endpoint": response.endpoint,
            "input_file_id": response.input_file_id,
            "resource_status": response.status,
            "request_counts_total": response.request_counts.total if response.request_counts else None,
            "output_file_id": response.output_file_id,
        }

    def _batches_list_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.batches.list()
        return {
            "object": response.object,
            "data_count": len(response.data),
        }

    def _batches_retrieve_row(self, client: OpenAI, batch_id: str) -> Dict[str, Any]:
        response = client.batches.retrieve(batch_id)
        return {
            "object": response.object,
            "id": response.id,
            "endpoint": response.endpoint,
            "resource_status": response.status,
        }

    def _batches_cancel_row(self, client: OpenAI, batch_id: str) -> Dict[str, Any]:
        response = client.batches.cancel(batch_id)
        return {
            "object": response.object,
            "id": response.id,
            "resource_status": response.status,
        }

    def _uploads_create_row(self, client: OpenAI) -> Dict[str, Any]:
        path = self.upload_probe()
        response = client.uploads.create(
            bytes=path.stat().st_size,
            filename=path.name,
            mime_type="text/plain",
            purpose="assistants",
        )
        return {
            "object": response.object,
            "id": response.id,
            "bytes": response.bytes,
            "filename": response.filename,
            "resource_status": response.status,
        }

    def _upload_parts_create_row(self, client: OpenAI, upload_id: str) -> Dict[str, Any]:
        with self.upload_probe().open("rb") as fh:
            response = client.uploads.parts.create(upload_id, data=fh)
        return {
            "object": response.object,
            "id": response.id,
            "upload_id": response.upload_id,
        }

    def _uploads_complete_row(self, client: OpenAI, upload_id: str, upload_part_id: str) -> Dict[str, Any]:
        response = client.uploads.complete(upload_id, part_ids=[upload_part_id])
        file_obj = getattr(response, "file", None)
        return {
            "object": response.object,
            "id": response.id,
            "resource_status": response.status,
            "file_id": getattr(file_obj, "id", None),
            "file_object": getattr(file_obj, "object", None),
        }

    def _uploads_cancel_row(self, client: OpenAI, upload_id: str) -> Dict[str, Any]:
        response = client.uploads.cancel(upload_id)
        return {
            "object": response.object,
            "id": response.id,
            "resource_status": response.status,
        }

    def _evals_create_row(self, client: OpenAI) -> Dict[str, Any]:
        response = self._raw_post(client, "/evals", {
            "name": "sdk-local-eval",
            "data_source_config": {"type": "custom", "item_schema": {}},
            "testing_criteria": [{
                "type": "string_check",
                "name": "contains_expected",
                "input": "{{ output }}",
                "operation": "like",
                "reference": "sdk eval ok",
            }],
            "metadata": {
                "prompt": "Reply exactly: sdk eval ok",
                "expected_substring": "sdk eval ok",
            },
        })
        return {"object": response.get("object"), "id": response.get("id"), "resource_name": response.get("name")}

    def _evals_list_row(self, client: OpenAI) -> Dict[str, Any]:
        response = self._raw_get(client, "/evals")
        data = response.get("data") if isinstance(response.get("data"), list) else []
        return {"object": response.get("object"), "data_count": len(data)}

    def _evals_retrieve_row(self, client: OpenAI, eval_id: str) -> Dict[str, Any]:
        response = self._raw_get(client, f"/evals/{eval_id}")
        return {"object": response.get("object"), "id": response.get("id"), "resource_name": response.get("name")}

    def _evals_update_row(self, client: OpenAI, eval_id: str) -> Dict[str, Any]:
        response = self._raw_post(client, f"/evals/{eval_id}", {"name": "sdk-local-eval-updated"})
        return {"object": response.get("object"), "id": response.get("id"), "resource_name": response.get("name")}

    def _evals_delete_row(self, client: OpenAI, eval_id: str) -> Dict[str, Any]:
        response = self._raw_delete(client, f"/evals/{eval_id}")
        return {"object": response.get("object"), "id": response.get("eval_id"), "deleted": bool(response.get("deleted"))}

    def _eval_runs_create_row(self, client: OpenAI, eval_id: str) -> Dict[str, Any]:
        response = self._raw_post(client, f"/evals/{eval_id}/runs", {
            "name": "sdk-local-eval-run",
            "data_source": {
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
        })
        result_counts = response.get("result_counts") if isinstance(response.get("result_counts"), dict) else {}
        return {
            "object": response.get("object"),
            "id": response.get("id"),
            "eval_id": response.get("eval_id"),
            "resource_status": response.get("status"),
            "result_counts_total": result_counts.get("total"),
        }

    def _eval_runs_list_row(self, client: OpenAI, eval_id: str) -> Dict[str, Any]:
        response = self._raw_get(client, f"/evals/{eval_id}/runs")
        data = response.get("data") if isinstance(response.get("data"), list) else []
        return {"object": response.get("object"), "data_count": len(data)}

    def _eval_runs_retrieve_row(self, client: OpenAI, eval_id: str, run_id: str) -> Dict[str, Any]:
        response = self._raw_get(client, f"/evals/{eval_id}/runs/{run_id}")
        return {
            "object": response.get("object"),
            "id": response.get("id"),
            "eval_id": response.get("eval_id"),
            "resource_status": response.get("status"),
        }

    def _eval_runs_cancel_row(self, client: OpenAI, eval_id: str, run_id: str) -> Dict[str, Any]:
        response = self._raw_post(client, f"/evals/{eval_id}/runs/{run_id}/cancel")
        return {
            "object": response.get("object"),
            "id": response.get("id"),
            "eval_id": response.get("eval_id"),
            "resource_status": response.get("status"),
        }

    def _eval_runs_delete_row(self, client: OpenAI, eval_id: str, run_id: str) -> Dict[str, Any]:
        response = self._raw_delete(client, f"/evals/{eval_id}/runs/{run_id}")
        return {"object": response.get("object"), "id": response.get("run_id"), "deleted": bool(response.get("deleted"))}

    def _eval_output_items_list_row(self, client: OpenAI, eval_id: str, run_id: str) -> Dict[str, Any]:
        response = self._raw_get(client, f"/evals/{eval_id}/runs/{run_id}/output_items")
        data = response.get("data") if isinstance(response.get("data"), list) else []
        return {
            "object": response.get("object"),
            "data_count": len(data),
            "first_id": data[0].get("id") if data else None,
        }

    def _eval_output_items_retrieve_row(self, client: OpenAI, eval_id: str, run_id: str, output_item_id: str) -> Dict[str, Any]:
        response = self._raw_get(client, f"/evals/{eval_id}/runs/{run_id}/output_items/{output_item_id}")
        return {
            "object": response.get("object"),
            "id": response.get("id"),
            "eval_id": response.get("eval_id"),
            "run_id": response.get("run_id"),
            "resource_status": response.get("status"),
        }

    def _files_create_row(self, client: OpenAI) -> Dict[str, Any]:
        with self.upload_probe().open("rb") as fh:
            response = client.files.create(file=fh, purpose="assistants")
        return {
            "object": response.object,
            "id": response.id,
            "filename": response.filename,
            "bytes": response.bytes,
        }

    def _files_list_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.files.list()
        return {
            "object": response.object,
            "data_count": len(response.data),
        }

    def _files_retrieve_row(self, client: OpenAI, file_id: str) -> Dict[str, Any]:
        response = client.files.retrieve(file_id)
        return {
            "object": response.object,
            "id": response.id,
            "filename": response.filename,
            "bytes": response.bytes,
        }

    def _files_content_row(self, client: OpenAI, file_id: str) -> Dict[str, Any]:
        response = client.files.content(file_id)
        return {"bytes": len(response.read())}

    def _files_delete_row(self, client: OpenAI, file_id: str) -> Dict[str, Any]:
        response = client.files.delete(file_id)
        return {
            "id": response.id,
            "object": getattr(response, "object", None),
            "deleted": bool(response.deleted),
        }

    def _vector_stores_create_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.vector_stores.create(name="sdk-proxy-smoke")
        return {
            "object": response.object,
            "id": response.id,
            "name": response.name,
        }

    def _vector_stores_list_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.vector_stores.list()
        return {
            "object": response.object,
            "data_count": len(response.data),
        }

    def _vector_stores_retrieve_row(self, client: OpenAI, store_id: str) -> Dict[str, Any]:
        response = client.vector_stores.retrieve(store_id)
        return {
            "object": response.object,
            "id": response.id,
            "name": response.name,
        }

    def _vector_store_files_create_row(self, client: OpenAI, store_id: str, file_id: str) -> Dict[str, Any]:
        response = client.vector_stores.files.create(
            vector_store_id=store_id,
            file_id=file_id,
            attributes={"source": "sdk-proxy-smoke"},
        )
        return {
            "object": response.object,
            "id": response.id,
            "vector_store_id": response.vector_store_id,
            "status": response.status,
        }

    def _vector_store_files_list_row(self, client: OpenAI, store_id: str) -> Dict[str, Any]:
        response = client.vector_stores.files.list(vector_store_id=store_id)
        return {
            "object": response.object,
            "data_count": len(response.data),
        }

    def _vector_store_files_retrieve_row(self, client: OpenAI, store_id: str, file_id: str) -> Dict[str, Any]:
        response = client.vector_stores.files.retrieve(file_id, vector_store_id=store_id)
        return {
            "object": response.object,
            "id": response.id,
            "vector_store_id": response.vector_store_id,
            "status": response.status,
        }

    def _vector_store_files_content_row(self, client: OpenAI, store_id: str, file_id: str) -> Dict[str, Any]:
        response = client.vector_stores.files.content(file_id, vector_store_id=store_id)
        return {
            "object": response.object,
            "data_count": len(response.data),
        }

    def _vector_store_files_delete_row(self, client: OpenAI, store_id: str, file_id: str) -> Dict[str, Any]:
        response = client.vector_stores.files.delete(file_id, vector_store_id=store_id)
        return {
            "id": response.id,
            "object": getattr(response, "object", None),
            "deleted": bool(response.deleted),
        }

    def _vector_store_file_batches_create_row(self, client: OpenAI, store_id: str, file_id: str) -> Dict[str, Any]:
        response = client.vector_stores.file_batches.create(
            vector_store_id=store_id,
            file_ids=[file_id],
            attributes={"source": "sdk-proxy-smoke-batch"},
        )
        return {
            "object": response.object,
            "id": response.id,
            "vector_store_id": response.vector_store_id,
            "resource_status": response.status,
            "file_counts_total": response.file_counts.total,
        }

    def _vector_store_file_batches_retrieve_row(self, client: OpenAI, store_id: str, batch_id: str) -> Dict[str, Any]:
        response = client.vector_stores.file_batches.retrieve(batch_id, vector_store_id=store_id)
        return {
            "object": response.object,
            "id": response.id,
            "vector_store_id": response.vector_store_id,
            "resource_status": response.status,
            "file_counts_total": response.file_counts.total,
        }

    def _vector_store_file_batches_files_row(self, client: OpenAI, store_id: str, batch_id: str) -> Dict[str, Any]:
        response = client.vector_stores.file_batches.list_files(batch_id, vector_store_id=store_id)
        return {
            "object": response.object,
            "data_count": len(response.data),
        }

    def _vector_store_file_batches_cancel_row(self, client: OpenAI, store_id: str, batch_id: str) -> Dict[str, Any]:
        response = client.vector_stores.file_batches.cancel(batch_id, vector_store_id=store_id)
        return {
            "object": response.object,
            "id": response.id,
            "vector_store_id": response.vector_store_id,
            "resource_status": response.status,
            "file_counts_total": response.file_counts.total,
        }

    def _vector_stores_delete_row(self, client: OpenAI, store_id: str) -> Dict[str, Any]:
        response = client.vector_stores.delete(store_id)
        return {
            "id": response.id,
            "object": getattr(response, "object", None),
            "deleted": bool(response.deleted),
        }

    def _transcription_row(self, client: OpenAI) -> Dict[str, Any]:
        with self.tiny_wav().open("rb") as fh:
            response = client.audio.transcriptions.create(model="gpt-4o-mini-transcribe", file=fh)
        return {
            "text_present": isinstance(getattr(response, "text", None), str),
            "text_len": len(getattr(response, "text", "") or ""),
        }

    def _speech_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input="sdk speech ok",
        )
        return {"bytes": len(response.read())}

    def _image_row(self, client: OpenAI) -> Dict[str, Any]:
        response = client.images.generate(
            model="gpt-image-1",
            prompt="A small clean icon of an OAuth bridge on a white background, no text",
            size="1024x1024",
        )
        first = response.data[0] if response.data else None
        return {
            "data_count": len(response.data or []),
            "b64_json_present": bool(getattr(first, "b64_json", None)) if first else False,
            "url_present": bool(getattr(first, "url", None)) if first else False,
        }

    def write_reports(self, sdk_base_url: str) -> None:
        REPORTS.mkdir(exist_ok=True)
        finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        payload = {
            "finished_at": finished_at,
            "sdk_base_url": sdk_base_url,
            "include_speech": self.include_speech,
            "include_images": self.include_images,
            "results": self.rows,
        }
        (REPORTS / "openai_sdk_proxy_smoke_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
        lines = [
            "# OpenAI SDK Proxy Smoke Report",
            "",
            f"- Finished: `{finished_at}`",
            f"- SDK base URL: `{sdk_base_url}`",
            f"- Include speech: `{self.include_speech}`",
            f"- Include images: `{self.include_images}`",
            "",
            "| Status | Test | Evidence |",
            "|---|---|---|",
        ]
        for row in self.rows:
            evidence = []
            for key, value in row.items():
                if key in {"name", "status"} or value is None:
                    continue
                evidence.append(f"{key}={value}")
            lines.append(f"| `{row['status']}` | `{row['name']}` | {'; '.join(evidence)} |")
        lines.append("")
        (REPORTS / "openai_sdk_proxy_smoke_latest.md").write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the local OAuth proxy through the official OpenAI Python SDK.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="Use 0 for an ephemeral port.")
    parser.add_argument("--skip-speech", action="store_true", help="Skip the SDK audio speech route.")
    parser.add_argument("--include-images", action="store_true", help="Also run SDK image generation.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/openai_sdk_proxy_smoke_latest.*.")
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
        return OpenAISDKProxySmoke(
            include_speech=not args.skip_speech,
            include_images=args.include_images,
        ).run(f"http://{args.host}:{port}/v1", write=not args.no_write)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
