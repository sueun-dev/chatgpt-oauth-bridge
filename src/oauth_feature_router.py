from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import os
import re
import shutil
import time
import uuid
import zipfile
import ast
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional

from openai_oauth_access import OpenAIOAuthAccess


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
DATA = ROOT / "data"
LOCAL_FILES = DATA / "files"
LOCAL_VECTORS = DATA / "vector_stores"
LOCAL_EVALS = DATA / "evals"
LOCAL_UPLOADS = DATA / "uploads"
LOCAL_BATCHES = DATA / "batches"
LOCAL_RESPONSES = DATA / "responses"
LOCAL_CHAT_COMPLETIONS = DATA / "chat_completions"
LOCAL_ASSISTANTS = DATA / "assistants"
LOCAL_THREADS = DATA / "threads"
LOCAL_CONVERSATIONS = DATA / "conversations"
LOCAL_CONTAINERS = DATA / "containers"
LOCAL_CHATKIT = DATA / "chatkit"
LOCAL_SKILLS = DATA / "skills"
LOCAL_REALTIME_CALLS = DATA / "realtime_calls"
LOCAL_AUDIO = DATA / "audio"
LOCAL_AUDIO_VOICE_CONSENTS = LOCAL_AUDIO / "voice_consents"
LOCAL_AUDIO_VOICES = LOCAL_AUDIO / "voices"
LOCAL_FINE_TUNING = DATA / "fine_tuning"
LOCAL_FINE_TUNING_JOBS = LOCAL_FINE_TUNING / "jobs"
LOCAL_FINE_TUNING_PERMISSIONS = LOCAL_FINE_TUNING / "checkpoint_permissions"
LOCAL_ORGANIZATION = DATA / "organization"
LOCAL_VIDEOS = DATA / "videos"
LOCAL_VIDEO_CHARACTERS = LOCAL_VIDEOS / "characters"
ORG_COLLECTION_KEYS = {
    "admin_api_keys",
    "api_keys",
    "audit_logs",
    "certificates",
    "groups",
    "hosted_tool_permissions",
    "invites",
    "model_permissions",
    "projects",
    "rate_limits",
    "roles",
    "service_accounts",
    "spend_alerts",
    "users",
}
ORG_USAGE_METRICS = {
    "audio_speeches",
    "audio_transcriptions",
    "code_interpreter_sessions",
    "completions",
    "embeddings",
    "file_search_calls",
    "images",
    "moderations",
    "vector_stores",
    "web_search_calls",
}
BUILT_IN_AUDIO_VOICES = [
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "onyx",
    "nova",
    "sage",
    "shimmer",
    "verse",
    "marin",
    "cedar",
]


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
        LOCAL_EVALS.mkdir(exist_ok=True)
        LOCAL_UPLOADS.mkdir(exist_ok=True)
        LOCAL_BATCHES.mkdir(exist_ok=True)
        LOCAL_RESPONSES.mkdir(exist_ok=True)
        LOCAL_CHAT_COMPLETIONS.mkdir(exist_ok=True)
        LOCAL_ASSISTANTS.mkdir(exist_ok=True)
        LOCAL_THREADS.mkdir(exist_ok=True)
        LOCAL_CONVERSATIONS.mkdir(exist_ok=True)
        LOCAL_CONTAINERS.mkdir(exist_ok=True)
        (LOCAL_CHATKIT / "sessions").mkdir(parents=True, exist_ok=True)
        (LOCAL_CHATKIT / "threads").mkdir(parents=True, exist_ok=True)
        (LOCAL_SKILLS / "local").mkdir(parents=True, exist_ok=True)
        LOCAL_REALTIME_CALLS.mkdir(parents=True, exist_ok=True)
        LOCAL_AUDIO_VOICE_CONSENTS.mkdir(parents=True, exist_ok=True)
        LOCAL_AUDIO_VOICES.mkdir(parents=True, exist_ok=True)
        LOCAL_FINE_TUNING_JOBS.mkdir(parents=True, exist_ok=True)
        LOCAL_FINE_TUNING_PERMISSIONS.mkdir(parents=True, exist_ok=True)
        LOCAL_ORGANIZATION.mkdir(parents=True, exist_ok=True)
        LOCAL_VIDEOS.mkdir(parents=True, exist_ok=True)
        LOCAL_VIDEO_CHARACTERS.mkdir(parents=True, exist_ok=True)

    def responses_create(self, input: str, *, instructions: str = "Answer directly.") -> Dict[str, Any]:
        text = self.oauth.codex_text(input, instructions=instructions)
        return {
            "object": "oauth_compat.response",
            "route": "codex_text",
            "model": self.oauth.text_model,
            "output_text": text,
        }

    def responses_input_tokens_estimate(self, input: Any, *, instructions: Optional[str] = None) -> Dict[str, Any]:
        text = self.input_to_plain_text(input)
        if instructions:
            text = f"{instructions}\n{text}"
        # This is intentionally a conservative local estimate, not OpenAI's hosted tokenizer.
        words = len(re.findall(r"\S+", text))
        chars = len(text)
        estimated_tokens = max(1, max(math.ceil(chars / 4), math.ceil(words * 1.35)))
        return {
            "object": "response.input_tokens.estimate",
            "input_tokens": estimated_tokens,
            "cached_input_tokens": 0,
            "total_tokens": estimated_tokens,
            "estimated": True,
            "method": "local_chars_words_estimate",
            "route": "local_input_token_estimate",
            "text_chars": chars,
            "text_words": words,
        }

    def responses_compact(self, input: Any, *, instructions: Optional[str] = None) -> Dict[str, Any]:
        prompt = self.input_to_plain_text(input)
        compact_instructions = instructions or (
            "Compact the input into a short durable summary. Preserve concrete "
            "names, ids, constraints, and decisions."
        )
        text = self.oauth.codex_text(prompt, instructions=compact_instructions)
        input_usage = self.responses_input_tokens_estimate(prompt, instructions=compact_instructions)
        output_tokens = int(self.responses_input_tokens_estimate(text).get("input_tokens", 1))
        return {
            "object": "oauth_compat.response.compaction",
            "route": "local_responses_compact_plus_codex_text",
            "model": self.oauth.text_model,
            "compacted_text": text,
            "encrypted_content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "usage": {
                "input_tokens": input_usage["input_tokens"],
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens": output_tokens,
                "output_tokens_details": {"reasoning_tokens": 0},
                "total_tokens": input_usage["input_tokens"] + output_tokens,
            },
        }

    def completions_create(self, prompt: str) -> Dict[str, Any]:
        text = self.oauth.codex_text(
            prompt,
            instructions="Complete the user's prompt. Return only the completion text.",
        )
        return {
            "object": "oauth_compat.completion",
            "route": "codex_text",
            "model": self.oauth.text_model,
            "text": text,
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

    def responses_save(self, payload: Dict[str, Any], input_items: list[Dict[str, Any]]) -> Dict[str, Any]:
        record = {
            "payload": payload,
            "input_items": input_items,
            "route": "local_response_store_plus_codex_text",
            "saved_at": int(time.time()),
        }
        self._save_response(record)
        return payload

    def responses_retrieve(self, response_id: str) -> Dict[str, Any]:
        return self._load_response(response_id)["payload"]

    def responses_cancel(self, response_id: str) -> Dict[str, Any]:
        record = self._load_response(response_id)
        payload = record["payload"]
        payload["status"] = "cancelled"
        payload["cancelled_at"] = time.time()
        record["payload"] = payload
        self._save_response(record)
        return payload

    def responses_delete(self, response_id: str) -> None:
        self._load_response(response_id)
        self._response_path(response_id).unlink(missing_ok=True)

    def response_input_items_list(self, response_id: str) -> Dict[str, Any]:
        record = self._load_response(response_id)
        return {
            "object": "list",
            "data": record.get("input_items", []),
            "route": record.get("route"),
        }

    def chat_completions_save(
        self,
        payload: Dict[str, Any],
        messages: list[Dict[str, Any]],
        assistant_message: Dict[str, Any],
    ) -> Dict[str, Any]:
        completion_id = str(payload.get("id") or "")
        store_message = {
            "id": f"msg_{uuid.uuid4().hex}",
            "role": "assistant",
            "content": assistant_message.get("content") if isinstance(assistant_message.get("content"), str) else "",
            "refusal": None,
        }
        record = {
            "payload": payload,
            "request_messages": messages,
            "messages": [store_message],
            "route": "local_chat_completion_store_plus_codex_text",
            "saved_at": int(time.time()),
        }
        self._save_chat_completion(record, completion_id)
        return payload

    def chat_completions_retrieve(self, completion_id: str) -> Dict[str, Any]:
        return self._load_chat_completion(completion_id)["payload"]

    def chat_completions_list(self) -> Dict[str, Any]:
        data = []
        for path in sorted(LOCAL_CHAT_COMPLETIONS.glob("chatcmpl_*.json")):
            data.append(json.loads(path.read_text())["payload"])
        return {
            "object": "list",
            "route": "local_chat_completion_store_plus_codex_text",
            "data": data,
        }

    def chat_completions_update(self, completion_id: str, *, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        record = self._load_chat_completion(completion_id)
        payload = record["payload"]
        if metadata is not None:
            payload["metadata"] = metadata
        record["payload"] = payload
        self._save_chat_completion(record, completion_id)
        return payload

    def chat_completions_delete(self, completion_id: str) -> Dict[str, Any]:
        self._load_chat_completion(completion_id)
        self._chat_completion_path(completion_id).unlink(missing_ok=True)
        return {"id": completion_id, "object": "chat.completion.deleted", "deleted": True}

    def chat_completion_messages_list(self, completion_id: str) -> Dict[str, Any]:
        record = self._load_chat_completion(completion_id)
        return {
            "object": "list",
            "route": record.get("route"),
            "data": record.get("messages", []),
        }

    def assistants_create(
        self,
        *,
        model: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[list[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        assistant = {
            "id": f"asst_local_{uuid.uuid4().hex}",
            "object": "assistant",
            "created_at": int(time.time()),
            "name": name,
            "description": description,
            "model": model,
            "instructions": instructions,
            "tools": tools or [],
            "metadata": metadata or {},
            "temperature": None,
            "top_p": None,
            "response_format": "auto",
            "tool_resources": {},
            "oauth_compat_route": "local_assistant_store_plus_codex_text",
        }
        self._save_assistant(assistant)
        return assistant

    def assistants_list(self) -> Dict[str, Any]:
        data = [json.loads(path.read_text()) for path in sorted(LOCAL_ASSISTANTS.glob("asst_local_*.json"))]
        return {"object": "list", "route": "local_assistant_store_plus_codex_text", "data": data}

    def assistants_retrieve(self, assistant_id: str) -> Dict[str, Any]:
        return self._load_assistant(assistant_id)

    def assistants_update(
        self,
        assistant_id: str,
        *,
        model: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[list[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        assistant = self._load_assistant(assistant_id)
        for key, value in {
            "model": model,
            "name": name,
            "description": description,
            "instructions": instructions,
            "tools": tools,
            "metadata": metadata,
        }.items():
            if value is not None:
                assistant[key] = value
        self._save_assistant(assistant)
        return assistant

    def assistants_delete(self, assistant_id: str) -> Dict[str, Any]:
        self._load_assistant(assistant_id)
        self._assistant_path(assistant_id).unlink(missing_ok=True)
        return {"id": assistant_id, "object": "assistant.deleted", "deleted": True}

    def threads_create(
        self,
        *,
        messages: Optional[list[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tool_resources: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        thread = {
            "id": f"thread_local_{uuid.uuid4().hex}",
            "object": "thread",
            "created_at": int(time.time()),
            "metadata": metadata or {},
            "tool_resources": tool_resources or {},
            "messages": [],
            "runs": [],
            "steps": [],
            "oauth_compat_route": "local_thread_store_plus_codex_text",
        }
        self._save_thread(thread)
        for item in messages or []:
            if isinstance(item, dict):
                self.thread_messages_create(
                    thread["id"],
                    role=str(item.get("role") or "user"),
                    content=item.get("content") if "content" in item else "",
                    metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else None,
                    attachments=item.get("attachments") if isinstance(item.get("attachments"), list) else None,
                )
        return self._thread_shape(self._load_thread(thread["id"]))

    def threads_retrieve(self, thread_id: str) -> Dict[str, Any]:
        return self._thread_shape(self._load_thread(thread_id))

    def threads_update(self, thread_id: str, *, metadata: Optional[Dict[str, Any]] = None, tool_resources: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        thread = self._load_thread(thread_id)
        if metadata is not None:
            thread["metadata"] = metadata
        if tool_resources is not None:
            thread["tool_resources"] = tool_resources
        self._save_thread(thread)
        return self._thread_shape(thread)

    def threads_delete(self, thread_id: str) -> Dict[str, Any]:
        self._load_thread(thread_id)
        self._thread_path(thread_id).unlink(missing_ok=True)
        return {"id": thread_id, "object": "thread.deleted", "deleted": True}

    def thread_messages_create(
        self,
        thread_id: str,
        *,
        role: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
        attachments: Optional[list[Dict[str, Any]]] = None,
        assistant_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        thread = self._load_thread(thread_id)
        message = self._thread_message_shape(
            thread_id=thread_id,
            role=role,
            content=content,
            metadata=metadata,
            attachments=attachments,
            assistant_id=assistant_id,
            run_id=run_id,
        )
        thread.setdefault("messages", []).append(message)
        self._save_thread(thread)
        return message

    def thread_messages_list(self, thread_id: str) -> Dict[str, Any]:
        thread = self._load_thread(thread_id)
        return {"object": "list", "route": "local_thread_store_plus_codex_text", "data": thread.get("messages", [])}

    def thread_messages_retrieve(self, thread_id: str, message_id: str) -> Dict[str, Any]:
        return self._find_thread_message(thread_id, message_id)

    def thread_messages_update(self, thread_id: str, message_id: str, *, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        thread = self._load_thread(thread_id)
        for message in thread.get("messages", []):
            if message.get("id") == message_id:
                if metadata is not None:
                    message["metadata"] = metadata
                self._save_thread(thread)
                return message
        raise FileNotFoundError(f"Unknown local thread message: {message_id}")

    def thread_messages_delete(self, thread_id: str, message_id: str) -> Dict[str, Any]:
        thread = self._load_thread(thread_id)
        before = len(thread.get("messages", []))
        thread["messages"] = [message for message in thread.get("messages", []) if message.get("id") != message_id]
        if len(thread["messages"]) == before:
            raise FileNotFoundError(f"Unknown local thread message: {message_id}")
        self._save_thread(thread)
        return {"id": message_id, "object": "thread.message.deleted", "deleted": True}

    def thread_runs_create(
        self,
        thread_id: str,
        *,
        assistant_id: str,
        instructions: Optional[str] = None,
        additional_instructions: Optional[str] = None,
        additional_messages: Optional[list[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        assistant = self._load_assistant(assistant_id)
        for item in additional_messages or []:
            if isinstance(item, dict):
                self.thread_messages_create(
                    thread_id,
                    role=str(item.get("role") or "user"),
                    content=item.get("content") if "content" in item else "",
                )
        thread = self._load_thread(thread_id)
        transcript = self._thread_transcript(thread)
        merged_instructions = "\n".join(part for part in [
            assistant.get("instructions"),
            instructions,
            additional_instructions,
            "Continue the thread as the assistant. Return only the assistant message.",
        ] if isinstance(part, str) and part.strip())
        output_text = self.oauth.codex_text(transcript or "Continue.", instructions=merged_instructions or "Continue the thread as the assistant.")
        run_id = f"run_local_{uuid.uuid4().hex}"
        assistant_message = self._thread_message_shape(
            thread_id=thread_id,
            role="assistant",
            content=output_text,
            assistant_id=assistant_id,
            run_id=run_id,
        )
        step_id = f"step_local_{uuid.uuid4().hex}"
        now = int(time.time())
        run = {
            "id": run_id,
            "object": "thread.run",
            "created_at": now,
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            "status": "completed",
            "started_at": now,
            "completed_at": now,
            "cancelled_at": None,
            "failed_at": None,
            "expires_at": now + 600,
            "model": model or assistant.get("model") or self.oauth.text_model,
            "instructions": merged_instructions or "",
            "tools": assistant.get("tools", []),
            "metadata": metadata or {},
            "parallel_tool_calls": True,
            "required_action": None,
            "last_error": None,
            "response_format": "auto",
            "tool_choice": "auto",
            "truncation_strategy": {"type": "auto", "last_messages": None},
            "usage": None,
            "oauth_compat_route": "local_assistant_thread_run_plus_codex_text",
        }
        step = {
            "id": step_id,
            "object": "thread.run.step",
            "created_at": now,
            "assistant_id": assistant_id,
            "thread_id": thread_id,
            "run_id": run_id,
            "type": "message_creation",
            "status": "completed",
            "completed_at": now,
            "cancelled_at": None,
            "failed_at": None,
            "expired_at": None,
            "last_error": None,
            "metadata": {},
            "step_details": {
                "type": "message_creation",
                "message_creation": {"message_id": assistant_message["id"]},
            },
            "usage": None,
        }
        thread.setdefault("messages", []).append(assistant_message)
        thread.setdefault("runs", []).append(run)
        thread.setdefault("steps", []).append(step)
        self._save_thread(thread)
        return run

    def thread_runs_list(self, thread_id: str) -> Dict[str, Any]:
        thread = self._load_thread(thread_id)
        return {"object": "list", "route": "local_assistant_thread_run_plus_codex_text", "data": thread.get("runs", [])}

    def thread_runs_retrieve(self, thread_id: str, run_id: str) -> Dict[str, Any]:
        return self._find_thread_run(thread_id, run_id)

    def thread_runs_update(self, thread_id: str, run_id: str, *, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        thread = self._load_thread(thread_id)
        for run in thread.get("runs", []):
            if run.get("id") == run_id:
                if metadata is not None:
                    run["metadata"] = metadata
                self._save_thread(thread)
                return run
        raise FileNotFoundError(f"Unknown local thread run: {run_id}")

    def thread_runs_cancel(self, thread_id: str, run_id: str) -> Dict[str, Any]:
        thread = self._load_thread(thread_id)
        for run in thread.get("runs", []):
            if run.get("id") == run_id:
                run["status"] = "cancelled"
                run["cancelled_at"] = int(time.time())
                self._save_thread(thread)
                return run
        raise FileNotFoundError(f"Unknown local thread run: {run_id}")

    def thread_runs_submit_tool_outputs(self, thread_id: str, run_id: str, *, tool_outputs: list[Dict[str, Any]]) -> Dict[str, Any]:
        run = self.thread_runs_update(thread_id, run_id, metadata={"tool_outputs_count": str(len(tool_outputs))})
        run["status"] = "completed"
        return run

    def thread_run_steps_list(self, thread_id: str, run_id: str) -> Dict[str, Any]:
        thread = self._load_thread(thread_id)
        steps = [step for step in thread.get("steps", []) if step.get("run_id") == run_id]
        return {"object": "list", "route": "local_assistant_thread_run_plus_codex_text", "data": steps}

    def thread_run_steps_retrieve(self, thread_id: str, run_id: str, step_id: str) -> Dict[str, Any]:
        thread = self._load_thread(thread_id)
        for step in thread.get("steps", []):
            if step.get("run_id") == run_id and step.get("id") == step_id:
                return step
        raise FileNotFoundError(f"Unknown local thread run step: {step_id}")

    def threads_create_and_run(
        self,
        *,
        assistant_id: str,
        thread: Optional[Dict[str, Any]] = None,
        instructions: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        thread_payload = thread if isinstance(thread, dict) else {}
        created_thread = self.threads_create(
            messages=thread_payload.get("messages") if isinstance(thread_payload.get("messages"), list) else None,
            metadata=thread_payload.get("metadata") if isinstance(thread_payload.get("metadata"), dict) else None,
            tool_resources=thread_payload.get("tool_resources") if isinstance(thread_payload.get("tool_resources"), dict) else None,
        )
        return self.thread_runs_create(
            created_thread["id"],
            assistant_id=assistant_id,
            instructions=instructions,
            metadata=metadata,
            model=model,
        )

    def chatkit_sessions_create(
        self,
        *,
        model: Optional[str] = None,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        session_id = f"cksession-local-{uuid.uuid4().hex}"
        now = int(time.time())
        session = {
            "id": session_id,
            "object": "chatkit.session",
            "created_at": now,
            "status": "active",
            "model": model or self.oauth.text_model,
            "thread_id": thread_id,
            "metadata": metadata or {},
            "route": "local_chatkit_session_store",
        }
        self._save_chatkit_session(session)
        return session

    def chatkit_sessions_cancel(self, session_id: str) -> Dict[str, Any]:
        session = self._load_chatkit_session(session_id)
        session["status"] = "cancelled"
        session["cancelled_at"] = int(time.time())
        self._save_chatkit_session(session)
        return session

    def chatkit_threads_create(
        self,
        *,
        items: Optional[list[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        thread_id = f"ckthread-local-{uuid.uuid4().hex}"
        now = int(time.time())
        thread = {
            "id": thread_id,
            "object": "chatkit.thread",
            "created_at": now,
            "metadata": metadata or {},
            "items": [],
            "route": "local_chatkit_thread_store",
        }
        for item in items or []:
            if not isinstance(item, dict):
                continue
            thread["items"].append(self._chatkit_item_shape(
                thread_id=thread_id,
                role=str(item.get("role") or "user"),
                content=item.get("content") if "content" in item else "",
                metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else None,
            ))
        self._save_chatkit_thread(thread)
        return self._chatkit_thread_shape(thread)

    def chatkit_threads_retrieve(self, thread_id: str) -> Dict[str, Any]:
        return self._chatkit_thread_shape(self._load_chatkit_thread(thread_id))

    def chatkit_thread_items_list(self, thread_id: str) -> Dict[str, Any]:
        thread = self._load_chatkit_thread(thread_id)
        return {
            "object": "list",
            "route": "local_chatkit_thread_store",
            "data": thread.get("items", []),
        }

    def conversations_create(
        self,
        *,
        items: Optional[list[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        conversation_id = f"conv-local-{uuid.uuid4().hex}"
        now = int(time.time())
        conversation = {
            "id": conversation_id,
            "object": "conversation",
            "created_at": now,
            "metadata": metadata or {},
            "items": [],
            "route": "local_conversation_store",
        }
        for item in (items or [])[:20]:
            if isinstance(item, dict):
                conversation["items"].append(self._conversation_item_shape(item))
        self._save_conversation(conversation)
        return self._conversation_shape(conversation)

    def conversations_retrieve(self, conversation_id: str) -> Dict[str, Any]:
        return self._conversation_shape(self._load_conversation(conversation_id))

    def conversations_update(
        self,
        conversation_id: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        conversation = self._load_conversation(conversation_id)
        if metadata is not None:
            conversation["metadata"] = metadata
        self._save_conversation(conversation)
        return self._conversation_shape(conversation)

    def conversations_delete(self, conversation_id: str) -> Dict[str, Any]:
        self._load_conversation(conversation_id)
        self._conversation_path(conversation_id).unlink(missing_ok=True)
        return {
            "id": conversation_id,
            "object": "conversation.deleted",
            "deleted": True,
            "oauth_compat_route": "local_conversation_store",
        }

    def conversation_items_create(self, conversation_id: str, *, items: list[Dict[str, Any]]) -> Dict[str, Any]:
        conversation = self._load_conversation(conversation_id)
        created = []
        for item in items[:20]:
            if not isinstance(item, dict):
                continue
            shaped = self._conversation_item_shape(item)
            conversation.setdefault("items", []).append(shaped)
            created.append(shaped)
        self._save_conversation(conversation)
        return self._conversation_item_list_shape(created)

    def conversation_items_list(
        self,
        conversation_id: str,
        *,
        limit: int = 20,
        order: str = "desc",
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        conversation = self._load_conversation(conversation_id)
        items = list(conversation.get("items", []))
        if order != "asc":
            items.reverse()
        start = 0
        if after:
            for index, item in enumerate(items):
                if item.get("id") == after:
                    start = index + 1
                    break
        safe_limit = max(1, min(int(limit), 100))
        page = items[start:start + safe_limit]
        return self._conversation_item_list_shape(page, has_more=start + safe_limit < len(items))

    def conversation_items_retrieve(self, conversation_id: str, item_id: str) -> Dict[str, Any]:
        conversation = self._load_conversation(conversation_id)
        for item in conversation.get("items", []):
            if item.get("id") == item_id:
                return item
        raise FileNotFoundError(f"Unknown local conversation item: {item_id}")

    def conversation_items_delete(self, conversation_id: str, item_id: str) -> Dict[str, Any]:
        conversation = self._load_conversation(conversation_id)
        items = [item for item in conversation.get("items", []) if item.get("id") != item_id]
        if len(items) == len(conversation.get("items", [])):
            raise FileNotFoundError(f"Unknown local conversation item: {item_id}")
        conversation["items"] = items
        self._save_conversation(conversation)
        return self._conversation_shape(conversation)

    def skills_list(
        self,
        *,
        limit: int = 100,
        order: str = "desc",
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        records = list(self._skills_registry().values())
        reverse = order != "asc"
        records.sort(key=lambda item: (int(item.get("created_at") or 0), str(item.get("id") or "")), reverse=reverse)
        start = 0
        if after:
            for index, record in enumerate(records):
                if record.get("id") == after:
                    start = index + 1
                    break
        safe_limit = max(0, min(int(limit), 100))
        page = records[start:start + safe_limit]
        return {
            "object": "list",
            "route": "local_skill_registry",
            "data": [self._skill_shape(record) for record in page],
            "first_id": page[0]["id"] if page else None,
            "last_id": page[-1]["id"] if page else None,
            "has_more": start + safe_limit < len(records),
        }

    def skills_create(
        self,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        bundle_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        skill_name = name or "local-skill"
        skill_id = f"skill-local-{self._safe_slug(skill_name)}-{uuid.uuid4().hex[:12]}"
        now = int(time.time())
        root = self._local_skill_dir(skill_id)
        version_dir = root / "versions" / "1"
        version_dir.mkdir(parents=True, exist_ok=True)
        self._write_skill_version_dir(
            version_dir,
            name=skill_name,
            description=description,
            content=content,
            bundle_bytes=bundle_bytes,
            filename=filename,
        )
        record = {
            "id": skill_id,
            "object": "skill",
            "created_at": now,
            "name": skill_name,
            "description": description or "",
            "default_version": "1",
            "latest_version": "1",
            "metadata": metadata or {},
            "source": "local_compat_skill_store",
            "read_only": False,
            "local_root": str(root),
            "route": "local_skill_registry",
        }
        self._save_local_skill_metadata(record)
        return self._skill_shape(record)

    def skills_retrieve(self, skill_id: str) -> Dict[str, Any]:
        return self._skill_shape(self._load_skill_record(skill_id))

    def skills_update_default_version(self, skill_id: str, *, default_version: str) -> Dict[str, Any]:
        record = self._load_skill_record(skill_id)
        self._require_writable_skill(record)
        if not self._skill_version_dir(record, default_version).exists():
            raise FileNotFoundError(f"Unknown local skill version: {default_version}")
        record["default_version"] = default_version
        self._save_local_skill_metadata(record)
        return self._skill_shape(record)

    def skills_delete(self, skill_id: str) -> Dict[str, Any]:
        record = self._load_skill_record(skill_id)
        self._require_writable_skill(record)
        shutil.rmtree(self._local_skill_dir(skill_id), ignore_errors=True)
        return {
            "id": skill_id,
            "object": "skill.deleted",
            "deleted": True,
            "oauth_compat_route": "local_skill_registry",
        }

    def skill_content(self, skill_id: str) -> tuple[bytes, str, Dict[str, Any]]:
        record = self._load_skill_record(skill_id)
        version = str(record.get("default_version") or "1")
        return self.skill_version_content(skill_id, version)

    def skill_versions_list(
        self,
        skill_id: str,
        *,
        limit: int = 100,
        order: str = "desc",
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        record = self._load_skill_record(skill_id)
        versions = self._skill_versions(record)
        reverse = order != "asc"
        versions.sort(key=lambda item: str(item.get("version") or ""), reverse=reverse)
        start = 0
        if after:
            for index, version in enumerate(versions):
                if version.get("id") == after or version.get("version") == after:
                    start = index + 1
                    break
        safe_limit = max(0, min(int(limit), 100))
        page = versions[start:start + safe_limit]
        return {
            "object": "list",
            "route": "local_skill_registry",
            "data": page,
            "first_id": page[0]["id"] if page else None,
            "last_id": page[-1]["id"] if page else None,
            "has_more": start + safe_limit < len(versions),
        }

    def skill_versions_create(
        self,
        skill_id: str,
        *,
        content: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        bundle_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        record = self._load_skill_record(skill_id)
        self._require_writable_skill(record)
        current = [
            int(path.name)
            for path in (self._local_skill_dir(skill_id) / "versions").iterdir()
            if path.is_dir() and path.name.isdigit()
        ]
        version = str(max(current or [0]) + 1)
        version_dir = self._skill_version_dir(record, version)
        version_dir.mkdir(parents=True, exist_ok=True)
        self._write_skill_version_dir(
            version_dir,
            name=str(record.get("name") or skill_id),
            description=description if description is not None else str(record.get("description") or ""),
            content=content,
            bundle_bytes=bundle_bytes,
            filename=filename,
        )
        record["latest_version"] = version
        record["default_version"] = version
        if metadata:
            merged = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
            record["metadata"] = {**merged, **metadata}
        self._save_local_skill_metadata(record)
        return self._skill_version_shape(record, version)

    def skill_version_retrieve(self, skill_id: str, version: str) -> Dict[str, Any]:
        record = self._load_skill_record(skill_id)
        if not self._skill_version_dir(record, version).exists():
            raise FileNotFoundError(f"Unknown local skill version: {version}")
        return self._skill_version_shape(record, version)

    def skill_version_delete(self, skill_id: str, version: str) -> Dict[str, Any]:
        record = self._load_skill_record(skill_id)
        self._require_writable_skill(record)
        version_dir = self._skill_version_dir(record, version)
        if not version_dir.exists():
            raise FileNotFoundError(f"Unknown local skill version: {version}")
        if str(record.get("default_version")) == version:
            raise ValueError("cannot delete the default local skill version")
        shutil.rmtree(version_dir, ignore_errors=True)
        return {
            "id": self._skill_version_id(skill_id, version),
            "object": "skill.version.deleted",
            "skill_id": skill_id,
            "version": version,
            "deleted": True,
            "oauth_compat_route": "local_skill_registry",
        }

    def skill_version_content(self, skill_id: str, version: str) -> tuple[bytes, str, Dict[str, Any]]:
        record = self._load_skill_record(skill_id)
        version_dir = self._skill_version_dir(record, version)
        if not version_dir.exists():
            raise FileNotFoundError(f"Unknown local skill version: {version}")
        data = self._zip_skill_dir(version_dir)
        version_record = self._skill_version_shape(record, version)
        return data, "application/zip", version_record

    def images_generate(self, prompt: str, output_path: Path | str, *, size: str = "1024x1024") -> Dict[str, Any]:
        path = self.oauth.codex_generate_image(prompt, output_path, size=size)
        return {
            "object": "oauth_compat.image",
            "route": "codex_image_generation",
            "size": size,
            "path": str(path),
        }

    def images_edit(
        self,
        image_path: Path | str,
        prompt: str,
        output_path: Path | str,
        *,
        size: str = "1024x1024",
    ) -> Dict[str, Any]:
        source_description = self.oauth.codex_vision(
            image_path,
            "Describe this source image in concise visual detail for a follow-up image edit.",
        )
        edit_prompt = "\n".join([
            "Create a new image that applies the requested edit to the source image.",
            f"Source image description: {source_description}",
            f"Requested edit: {prompt}",
            "Preserve important composition, subject identity, and visual context where possible.",
        ])
        path = self.oauth.codex_generate_image(edit_prompt, output_path, size=size)
        return {
            "object": "oauth_compat.image.edit",
            "route": "codex_vision_plus_image_generation_edit",
            "size": size,
            "path": str(path),
            "source_description_chars": len(source_description),
        }

    def images_variation(
        self,
        image_path: Path | str,
        output_path: Path | str,
        *,
        size: str = "1024x1024",
    ) -> Dict[str, Any]:
        source_description = self.oauth.codex_vision(
            image_path,
            "Describe this image in concise visual detail for creating a variation.",
        )
        variation_prompt = "\n".join([
            "Create a new image variation inspired by the source image.",
            f"Source image description: {source_description}",
            "Keep the main subject and composition recognizable, but vary style, lighting, and small details.",
        ])
        path = self.oauth.codex_generate_image(variation_prompt, output_path, size=size)
        return {
            "object": "oauth_compat.image.variation",
            "route": "codex_vision_plus_image_generation_variation",
            "size": size,
            "path": str(path),
            "source_description_chars": len(source_description),
        }

    def audio_voices_list(self) -> Dict[str, Any]:
        data = [self._audio_builtin_voice_shape(name) for name in BUILT_IN_AUDIO_VOICES]
        data.extend(
            json.loads(path.read_text())
            for path in sorted(LOCAL_AUDIO_VOICES.glob("voice-local-*.json"))
        )
        return {
            "object": "list",
            "route": "local_audio_voice_catalog",
            "data": data,
            "has_more": False,
            "first_id": data[0].get("id") if data else None,
            "last_id": data[-1].get("id") if data else None,
        }

    def audio_voices_create(
        self,
        *,
        name: str,
        consent: str,
        audio_sample_path: Path | str,
        mime_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        consent_record = self.audio_voice_consents_retrieve(consent)
        src = Path(audio_sample_path)
        if not src.exists():
            raise FileNotFoundError(f"Missing local audio sample: {src}")
        voice_id = f"voice-local-{uuid.uuid4().hex}"
        voice_dir = LOCAL_AUDIO_VOICES / voice_id
        voice_dir.mkdir(parents=True, exist_ok=True)
        sample_path = voice_dir / "audio_sample.bin"
        shutil.copyfile(src, sample_path)
        record = {
            "id": voice_id,
            "object": "audio.voice",
            "created_at": int(time.time()),
            "name": name,
            "consent": consent_record.get("id"),
            "type": "local_custom_voice_metadata",
            "route": "local_audio_voice_catalog",
            "oauth_compat_route": "local_audio_voice_catalog",
            "mime_type": mime_type,
            "bytes": sample_path.stat().st_size,
            "local_sample_path": str(sample_path),
            "hosted_voice_created": False,
            "official_route_note": (
                "Hosted custom voice creation requires eligible Platform API credentials. "
                "This local record lets apps test custom-voice metadata and voice IDs."
            ),
        }
        self._audio_voice_path(voice_id).write_text(json.dumps(record, indent=2, sort_keys=True))
        return record

    def audio_voice_consents_create(
        self,
        *,
        name: str,
        language: str,
        recording_path: Path | str,
        mime_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        if not isinstance(language, str) or not language.strip():
            raise ValueError("language must be a non-empty string")
        src = Path(recording_path)
        if not src.exists():
            raise FileNotFoundError(f"Missing local voice consent recording: {src}")
        consent_id = f"cons-local-{uuid.uuid4().hex}"
        consent_dir = LOCAL_AUDIO_VOICE_CONSENTS / consent_id
        consent_dir.mkdir(parents=True, exist_ok=True)
        recording_dst = consent_dir / "recording.bin"
        shutil.copyfile(src, recording_dst)
        record = {
            "id": consent_id,
            "object": "audio.voice_consent",
            "created_at": int(time.time()),
            "name": name,
            "language": language,
            "route": "local_audio_voice_consent_store",
            "oauth_compat_route": "local_audio_voice_consent_store",
            "mime_type": mime_type,
            "bytes": recording_dst.stat().st_size,
            "local_recording_path": str(recording_dst),
            "hosted_consent_created": False,
            "official_route_note": (
                "Hosted voice consent upload is limited to eligible Platform accounts. "
                "This local record is for SDK/app workflow compatibility only."
            ),
        }
        self._audio_voice_consent_path(consent_id).write_text(json.dumps(record, indent=2, sort_keys=True))
        return record

    def audio_voice_consents_list(self) -> Dict[str, Any]:
        data = [
            json.loads(path.read_text())
            for path in sorted(LOCAL_AUDIO_VOICE_CONSENTS.glob("cons-local-*/metadata.json"))
        ]
        return {
            "object": "list",
            "route": "local_audio_voice_consent_store",
            "data": data,
            "has_more": False,
            "first_id": data[0].get("id") if data else None,
            "last_id": data[-1].get("id") if data else None,
        }

    def audio_voice_consents_retrieve(self, consent_id: str) -> Dict[str, Any]:
        path = self._audio_voice_consent_path(consent_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local voice consent: {consent_id}")
        return json.loads(path.read_text())

    def audio_voice_consents_update(self, consent_id: str, *, name: str) -> Dict[str, Any]:
        record = self.audio_voice_consents_retrieve(consent_id)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        record["name"] = name
        record["updated_at"] = int(time.time())
        self._audio_voice_consent_path(consent_id).write_text(json.dumps(record, indent=2, sort_keys=True))
        return record

    def audio_voice_consents_delete(self, consent_id: str) -> Dict[str, Any]:
        self.audio_voice_consents_retrieve(consent_id)
        shutil.rmtree(LOCAL_AUDIO_VOICE_CONSENTS / consent_id, ignore_errors=True)
        return {
            "id": consent_id,
            "object": "audio.voice_consent.deleted",
            "deleted": True,
            "oauth_compat_route": "local_audio_voice_consent_store",
        }

    def audio_speech_create(self, text: str, output_path: Path | str, *, voice: Optional[Any] = None) -> Dict[str, Any]:
        path = self.oauth.realtime_say_to_pcm(text, output_path)
        return {
            "object": "oauth_compat.audio.speech",
            "route": "realtime_websocket_audio",
            "format": "pcm16",
            "path": str(path),
            "bytes": Path(path).stat().st_size,
            "voice": voice,
        }

    def audio_transcriptions_create(self, audio_path: Path | str) -> Dict[str, Any]:
        payload = self.oauth.official_transcribe_audio(audio_path)
        payload["route"] = "official_audio_transcriptions"
        return payload

    def audio_translations_create(self, audio_path: Path | str, *, prompt: Optional[str] = None) -> Dict[str, Any]:
        transcription = self.audio_transcriptions_create(audio_path)
        if int(transcription.get("_http_status", 200) or 200) >= 400:
            return transcription
        transcript = transcription.get("text")
        if not isinstance(transcript, str) or not transcript.strip():
            raise ValueError("Transcription did not return a non-empty text field.")
        instructions = (
            "Translate the supplied transcript into natural English. Return only "
            "the translated text. If it is already English, return it unchanged."
        )
        if prompt:
            instructions = f"{instructions}\nUser translation hint: {prompt}"
        translated = self.oauth.codex_text(transcript, instructions=instructions)
        return {
            "object": "audio.translation",
            "route": "official_audio_transcriptions_plus_codex_translation",
            "text": translated,
            "source_text_chars": len(transcript),
            "transcription_route": transcription.get("route"),
            "translation_model": self.oauth.text_model,
        }

    def realtime_sessions_create(self, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        request = dict(body or {})
        expires_after = request.pop("expires_after", None)
        if not isinstance(expires_after, dict):
            expires_after = None
        nested_session = request.pop("session", None)
        session = dict(nested_session) if isinstance(nested_session, dict) else request
        session.setdefault("type", "realtime")
        if not isinstance(session.get("model"), str) or not str(session.get("model")).strip():
            session["model"] = self.oauth.realtime_model
        upstream = self.oauth.realtime_client_secret_payload(
            session=session,
            expires_after=expires_after,
        )
        return self._realtime_session_alias_payload(
            upstream,
            session=session,
            requested_route="/v1/realtime/sessions",
            route="official_realtime_client_secrets_session_alias",
            object_name="realtime.session",
        )

    def realtime_transcription_sessions_create(self, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        request = dict(body or {})
        expires_after = request.pop("expires_after", None)
        if not isinstance(expires_after, dict):
            expires_after = None
        nested_session = request.pop("session", None)
        session = dict(nested_session) if isinstance(nested_session, dict) else request
        if not session:
            session = {
                "type": "transcription",
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "transcription": {"model": "gpt-4o-mini-transcribe"},
                        "turn_detection": {"type": "server_vad"},
                    },
                },
            }
        session.setdefault("type", "transcription")
        upstream = self.oauth.realtime_transcription_session(
            session=session,
            expires_after=expires_after,
        )
        return self._realtime_session_alias_payload(
            upstream,
            session=session,
            requested_route="/v1/realtime/transcription_sessions",
            route="official_realtime_client_secrets_transcription_alias",
            object_name="realtime.transcription_session",
        )

    def _realtime_session_alias_payload(
        self,
        upstream: Any,
        *,
        session: Dict[str, Any],
        requested_route: str,
        route: str,
        object_name: str,
    ) -> Dict[str, Any]:
        upstream_payload = upstream if isinstance(upstream, dict) else {"value": upstream}
        client_secret = upstream_payload.get("client_secret")
        if not isinstance(client_secret, dict):
            client_secret = {}
        value = upstream_payload.get("value")
        if isinstance(value, str) and value:
            client_secret.setdefault("value", value)
        expires_at = upstream_payload.get("expires_at")
        if expires_at is not None:
            client_secret.setdefault("expires_at", expires_at)
        return {
            "id": f"realtime_alias_{uuid.uuid4().hex}",
            "object": object_name,
            "created_at": int(time.time()),
            "model": session.get("model"),
            "session": session,
            "client_secret": client_secret,
            "oauth_compat_route": route,
            "requested_route": requested_route,
            "upstream_route": "/v1/realtime/client_secrets",
            "upstream_object": upstream_payload.get("object"),
            "_http_status": upstream_payload.get("_http_status"),
        }

    def realtime_call_lifecycle(self, call_id: str, action: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if action not in {"accept", "hangup", "refer", "reject"}:
            raise ValueError(f"Unsupported Realtime call lifecycle action: {action}")
        payload = body if isinstance(body, dict) else {}
        now = int(time.time())
        status_by_action = {
            "accept": "in_progress",
            "hangup": "completed",
            "refer": "referred",
            "reject": "rejected",
        }
        existing: Dict[str, Any] = {}
        path = self._realtime_call_path(call_id)
        if path.exists():
            existing = json.loads(path.read_text())
        record = {
            "id": call_id,
            "object": "realtime.call",
            "created_at": existing.get("created_at", now),
            "updated_at": now,
            "status": status_by_action[action],
            "last_action": action,
            "route": "local_realtime_call_lifecycle_state",
            "oauth_compat_route": "local_realtime_call_lifecycle_state",
            "requested_route": f"/v1/realtime/calls/{call_id}/{action}",
            "upstream_route": "/v1/realtime/calls",
            "official_route_note": (
                "Official Realtime call creation accepted OAuth, but lifecycle "
                "mutations need a real call id. This local handler records app "
                "state without claiming hosted lifecycle mutation proof."
            ),
            "request": payload,
            "events": [
                *existing.get("events", []),
                {"action": action, "at": now, "request": payload},
            ],
        }
        path.write_text(json.dumps(record, indent=2, sort_keys=True))
        return record

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
        dst.mkdir(exist_ok=True)
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
            "local_content_path": str(src),
        }
        (dst / "metadata.json").write_text(json.dumps(record, indent=2, sort_keys=True))
        return record

    def files_create_local_content(
        self,
        *,
        filename: str,
        content: bytes,
        purpose: str,
        mime_type: str = "application/octet-stream",
        route: str = "local_file_content",
    ) -> Dict[str, Any]:
        file_id = f"file-local-{uuid.uuid4().hex}"
        ARTIFACTS.mkdir(exist_ok=True)
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name) or "file.bin"
        content_path = ARTIFACTS / f"{file_id}_{safe_name}"
        content_path.write_bytes(content)
        dst = LOCAL_FILES / file_id
        dst.mkdir(exist_ok=True)
        record = {
            "id": file_id,
            "object": "oauth_compat.file",
            "route": route,
            "uri": f"local://{file_id}",
            "filename": filename,
            "purpose": purpose,
            "bytes": len(content),
            "mime_type": mime_type,
            "status": "processed",
            "created_at": int(time.time()),
            "download_url_present": False,
            "download_url_host": None,
            "local_metadata_path": str(dst / "metadata.json"),
            "local_content_path": str(content_path),
        }
        (dst / "metadata.json").write_text(json.dumps(record, indent=2, sort_keys=True))
        return record

    def files_list(self) -> Dict[str, Any]:
        records = []
        for meta in sorted(LOCAL_FILES.glob("*/metadata.json")):
            records.append(json.loads(meta.read_text()))
        return {"object": "oauth_compat.list", "route": "local_file_metadata", "data": records}

    def files_retrieve(self, file_id: str) -> Dict[str, Any]:
        path = self._file_metadata_path(file_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local file metadata: {file_id}")
        return json.loads(path.read_text())

    def files_content(self, file_id: str) -> tuple[bytes, str, Dict[str, Any]]:
        record = self.files_retrieve(file_id)
        local_content_path = record.get("local_content_path")
        if not isinstance(local_content_path, str):
            raise FileNotFoundError(f"No local content path recorded for file: {file_id}")
        path = Path(local_content_path)
        if not path.exists():
            raise FileNotFoundError(f"Local file content is missing: {file_id}")
        content_type = record.get("mime_type") if isinstance(record.get("mime_type"), str) else "application/octet-stream"
        return path.read_bytes(), content_type, record

    def files_delete(self, file_id: str) -> Dict[str, Any]:
        record = self.files_retrieve(file_id)
        local_content_path = record.get("local_content_path")
        if isinstance(local_content_path, str):
            path = Path(local_content_path)
            if path.exists() and ARTIFACTS in path.parents:
                path.unlink()
        metadata_path = self._file_metadata_path(file_id)
        metadata_path.unlink(missing_ok=True)
        parent = metadata_path.parent
        try:
            parent.rmdir()
        except OSError:
            pass
        return {"id": file_id, "object": "file", "deleted": True, "oauth_compat_route": record.get("route")}

    def containers_create(
        self,
        *,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_after: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        container_id = f"cntr-local-{uuid.uuid4().hex}"
        now = int(time.time())
        record = {
            "id": container_id,
            "object": "container",
            "created_at": now,
            "name": name,
            "status": "running",
            "metadata": metadata or {},
            "expires_after": expires_after,
            "route": "local_container_store",
            "local_path": str(self._container_dir(container_id)),
        }
        self._container_files_dir(container_id).mkdir(parents=True, exist_ok=True)
        self._save_container(record)
        return record

    def containers_list(self) -> Dict[str, Any]:
        records = [
            json.loads(path.read_text())
            for path in sorted(LOCAL_CONTAINERS.glob("cntr-local-*/metadata.json"))
        ]
        return {"object": "list", "route": "local_container_store", "data": records}

    def containers_retrieve(self, container_id: str) -> Dict[str, Any]:
        return self._load_container(container_id)

    def containers_delete(self, container_id: str) -> Dict[str, Any]:
        record = self._load_container(container_id)
        root = self._container_dir(container_id)
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        root.rmdir()
        return {"id": container_id, "object": "container.deleted", "deleted": True, "oauth_compat_route": record.get("route")}

    def container_files_create(
        self,
        container_id: str,
        source_path: Path | str,
        *,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._load_container(container_id)
        src = Path(source_path)
        data = src.read_bytes()
        file_id = f"cfile-local-{uuid.uuid4().hex}"
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename or src.name).name) or "file.bin"
        content_path = self._container_files_dir(container_id) / f"{file_id}_{safe_name}"
        content_path.write_bytes(data)
        record = {
            "id": file_id,
            "object": "container.file",
            "container_id": container_id,
            "created_at": int(time.time()),
            "filename": filename or src.name,
            "bytes": len(data),
            "mime_type": mime_type or "application/octet-stream",
            "route": "local_container_file_store",
            "local_content_path": str(content_path),
            "local_metadata_path": str(self._container_file_metadata_path(container_id, file_id)),
        }
        self._container_file_metadata_path(container_id, file_id).write_text(json.dumps(record, indent=2, sort_keys=True))
        return record

    def container_files_list(self, container_id: str) -> Dict[str, Any]:
        self._load_container(container_id)
        records = [
            json.loads(path.read_text())
            for path in sorted(self._container_files_dir(container_id).glob("*.metadata.json"))
        ]
        return {"object": "list", "route": "local_container_file_store", "data": records}

    def container_files_retrieve(self, container_id: str, file_id: str) -> Dict[str, Any]:
        self._load_container(container_id)
        path = self._container_file_metadata_path(container_id, file_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local container file: {file_id}")
        return json.loads(path.read_text())

    def container_files_content(self, container_id: str, file_id: str) -> tuple[bytes, str, Dict[str, Any]]:
        record = self.container_files_retrieve(container_id, file_id)
        local_content_path = record.get("local_content_path")
        if not isinstance(local_content_path, str):
            raise FileNotFoundError(f"No local container file content path recorded: {file_id}")
        path = Path(local_content_path)
        if not path.exists():
            raise FileNotFoundError(f"Local container file content is missing: {file_id}")
        content_type = record.get("mime_type") if isinstance(record.get("mime_type"), str) else "application/octet-stream"
        return path.read_bytes(), content_type, record

    def uploads_create(
        self,
        *,
        bytes: int,
        filename: str,
        mime_type: str,
        purpose: str,
        expires_after: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if bytes < 0:
            raise ValueError("bytes must be non-negative")
        upload_id = f"upload-local-{uuid.uuid4().hex}"
        now = int(time.time())
        record = {
            "id": upload_id,
            "object": "oauth_compat.upload",
            "route": "local_upload_session_plus_chatgpt_backend_files",
            "bytes": bytes,
            "created_at": now,
            "expires_at": now + 3600,
            "filename": filename,
            "mime_type": mime_type,
            "purpose": purpose,
            "status": "pending",
            "expires_after": expires_after or {},
            "parts": [],
            "file": None,
        }
        self._save_upload(record)
        return self._upload_summary(record)

    def upload_parts_create(self, upload_id: str, data: bytes) -> Dict[str, Any]:
        record = self._load_upload(upload_id)
        if record.get("status") != "pending":
            raise ValueError(f"Upload is not pending: {upload_id}")
        if len(data) > 64 * 1024 * 1024:
            raise ValueError("upload parts must be at most 64 MB")
        part_id = f"uploadpart-local-{uuid.uuid4().hex}"
        parts_dir = self._upload_parts_dir(upload_id)
        parts_dir.mkdir(parents=True, exist_ok=True)
        part_path = parts_dir / f"{part_id}.bin"
        part_path.write_bytes(data)
        part = {
            "id": part_id,
            "object": "oauth_compat.upload.part",
            "route": record.get("route"),
            "upload_id": upload_id,
            "created_at": int(time.time()),
            "bytes": len(data),
            "local_path": str(part_path),
        }
        record.setdefault("parts", []).append(part)
        self._save_upload(record)
        return self._upload_part_summary(part)

    def uploads_complete(self, upload_id: str, part_ids: list[str], *, md5: Optional[str] = None) -> Dict[str, Any]:
        record = self._load_upload(upload_id)
        if record.get("status") != "pending":
            raise ValueError(f"Upload is not pending: {upload_id}")
        if not part_ids:
            raise ValueError("part_ids must contain at least one part id")
        parts_by_id = {
            part.get("id"): part
            for part in record.get("parts", [])
            if isinstance(part, dict) and isinstance(part.get("id"), str)
        }
        chunks = []
        for part_id in part_ids:
            part = parts_by_id.get(part_id)
            if not isinstance(part, dict):
                raise FileNotFoundError(f"Unknown local upload part: {part_id}")
            part_path = Path(str(part.get("local_path") or ""))
            if not part_path.exists():
                raise FileNotFoundError(f"Local upload part content is missing: {part_id}")
            chunks.append(part_path.read_bytes())
        content = b"".join(chunks)
        expected_bytes = int(record.get("bytes", 0) or 0)
        if len(content) != expected_bytes:
            raise ValueError(f"completed upload byte count {len(content)} did not match declared bytes {expected_bytes}")
        if md5:
            hex_digest = hashlib.md5(content).hexdigest()
            b64_digest = base64.b64encode(hashlib.md5(content).digest()).decode("ascii")
            if md5 not in {hex_digest, b64_digest}:
                raise ValueError("completed upload md5 did not match content")
        ARTIFACTS.mkdir(exist_ok=True)
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(str(record.get("filename") or "upload.bin")).name) or "upload.bin"
        completed_path = ARTIFACTS / f"compat_upload_complete_{uuid.uuid4().hex}_{safe_name}"
        completed_path.write_bytes(content)
        file_record = self.files_create(completed_path, purpose=str(record.get("purpose") or "assistants"))
        if int(file_record.get("_http_status", 200) or 200) >= 400:
            raise RuntimeError(f"ChatGPT backend file upload failed: {file_record}")
        record["status"] = "completed"
        record["completed_at"] = int(time.time())
        record["completed_part_ids"] = part_ids
        record["completed_local_path"] = str(completed_path)
        record["file"] = file_record
        self._save_upload(record)
        return self._upload_summary(record)

    def uploads_cancel(self, upload_id: str) -> Dict[str, Any]:
        record = self._load_upload(upload_id)
        if record.get("status") == "completed":
            raise ValueError(f"Upload is already completed: {upload_id}")
        for part in record.get("parts", []):
            if isinstance(part, dict) and isinstance(part.get("local_path"), str):
                Path(part["local_path"]).unlink(missing_ok=True)
        record["status"] = "cancelled"
        record["cancelled_at"] = int(time.time())
        self._save_upload(record)
        return self._upload_summary(record)

    def moderations_create(self, input_value: Any, *, model: str = "local-heuristic-moderation") -> Dict[str, Any]:
        inputs = input_value if isinstance(input_value, list) else [input_value]
        results = []
        for item in inputs:
            text = self.input_to_plain_text(item)
            results.append(self._moderation_result(text))
        return {
            "id": f"modr-local-{uuid.uuid4().hex}",
            "model": model,
            "results": results,
            "route": "local_heuristic_moderation",
        }

    def batches_create(
        self,
        *,
        input_file_id: str,
        endpoint: str,
        completion_window: str,
        metadata: Optional[Dict[str, Any]] = None,
        output_expires_after: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        batch_id = f"batch-local-{uuid.uuid4().hex}"
        now = int(time.time())
        record = {
            "id": batch_id,
            "object": "oauth_compat.batch",
            "route": "local_batch_processor",
            "input_file_id": input_file_id,
            "endpoint": endpoint,
            "completion_window": completion_window,
            "metadata": metadata or {},
            "output_expires_after": output_expires_after or {},
            "created_at": now,
            "in_progress_at": now,
            "expires_at": now + 86400,
            "status": "in_progress",
            "request_counts": {"total": 0, "completed": 0, "failed": 0},
            "output_file_id": None,
            "error_file_id": None,
            "errors": None,
        }
        if str((metadata or {}).get("local_defer", "")).lower() == "true":
            self._save_batch(record)
            return self._batch_summary(record)
        content, _content_type, _file_record = self.files_content(input_file_id)
        output_lines: list[str] = []
        error_lines: list[str] = []
        total = 0
        completed = 0
        failed = 0
        for index, line in enumerate(content.decode("utf-8", errors="replace").splitlines()):
            if not line.strip():
                continue
            total += 1
            custom_id = f"request-{index}"
            try:
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError("batch input line must be a JSON object")
                custom_id = str(item.get("custom_id") or custom_id)
                method = str(item.get("method") or "POST").upper()
                url = str(item.get("url") or endpoint)
                body = item.get("body") if isinstance(item.get("body"), dict) else {}
                response_body = self._local_batch_request_body(method=method, url=url, endpoint=endpoint, body=body)
                output_lines.append(json.dumps({
                    "id": f"batch_req_local_{uuid.uuid4().hex}",
                    "custom_id": custom_id,
                    "response": {
                        "status_code": 200,
                        "request_id": f"req_local_{uuid.uuid4().hex}",
                        "body": response_body,
                    },
                    "error": None,
                }, sort_keys=True))
                completed += 1
            except Exception as exc:
                failed += 1
                error_lines.append(json.dumps({
                    "custom_id": custom_id,
                    "error": {
                        "message": str(exc)[:600],
                        "type": type(exc).__name__,
                    },
                }, sort_keys=True))
        output_file_id = None
        error_file_id = None
        if output_lines:
            output_file = self.files_create_local_content(
                filename=f"{batch_id}_output.jsonl",
                content=("\n".join(output_lines) + "\n").encode("utf-8"),
                purpose="batch_output",
                mime_type="application/jsonl",
                route="local_batch_output_file",
            )
            output_file_id = output_file["id"]
        if error_lines:
            error_file = self.files_create_local_content(
                filename=f"{batch_id}_errors.jsonl",
                content=("\n".join(error_lines) + "\n").encode("utf-8"),
                purpose="batch_error",
                mime_type="application/jsonl",
                route="local_batch_error_file",
            )
            error_file_id = error_file["id"]
        finished_at = int(time.time())
        record.update({
            "status": "completed",
            "finalizing_at": finished_at,
            "completed_at": finished_at,
            "request_counts": {"total": total, "completed": completed, "failed": failed},
            "output_file_id": output_file_id,
            "error_file_id": error_file_id,
        })
        self._save_batch(record)
        return self._batch_summary(record)

    def batches_list(self) -> Dict[str, Any]:
        data = []
        for path in sorted(LOCAL_BATCHES.glob("batch-local-*.json")):
            data.append(self._batch_summary(json.loads(path.read_text())))
        return {"object": "oauth_compat.list", "route": "local_batch_processor", "data": data}

    def batches_retrieve(self, batch_id: str) -> Dict[str, Any]:
        return self._batch_summary(self._load_batch(batch_id))

    def batches_cancel(self, batch_id: str) -> Dict[str, Any]:
        record = self._load_batch(batch_id)
        if record.get("status") != "completed":
            now = int(time.time())
            record["status"] = "cancelled"
            record["cancelling_at"] = now
            record["cancelled_at"] = now
            self._save_batch(record)
        return self._batch_summary(record)

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

    def vector_stores_list(self) -> Dict[str, Any]:
        records = []
        for path in sorted(LOCAL_VECTORS.glob("vs-local-*.json")):
            store = json.loads(path.read_text())
            records.append(self._vector_store_summary(store))
        return {"object": "oauth_compat.list", "route": "local_vector_store_plus_oauth_embeddings", "data": records}

    def vector_stores_retrieve(self, store_id: str) -> Dict[str, Any]:
        return self._vector_store_summary(self._load_vector_store(store_id))

    def vector_stores_delete(self, store_id: str) -> Dict[str, Any]:
        store = self._load_vector_store(store_id)
        self._vector_path(store_id).unlink(missing_ok=True)
        return {
            "id": store_id,
            "object": "vector_store.deleted",
            "deleted": True,
            "oauth_compat_route": store.get("route"),
        }

    def vector_stores_add_text(self, store_id: str, text: str, *, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._vector_stores_add_text(store_id, text, metadata=metadata)

    def vector_store_files_create(self, store_id: str, file_id: str, *, attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        content, _content_type, file_record = self.files_content(file_id)
        text = content.decode("utf-8", errors="replace").strip()
        if not text:
            text = str(file_record.get("filename") or file_id)
        metadata = {
            "file_id": file_id,
            "filename": file_record.get("filename"),
            "attributes": attributes or {},
        }
        self._vector_stores_add_text(store_id, text, metadata=metadata, file_id=file_id)
        return self.vector_store_files_retrieve(store_id, file_id)

    def vector_store_files_list(self, store_id: str) -> Dict[str, Any]:
        store = self._load_vector_store(store_id)
        data = [self._vector_store_file_summary(store, item) for item in store.get("items", []) if item.get("file_id")]
        return {"object": "oauth_compat.list", "route": store.get("route"), "data": data}

    def vector_store_files_retrieve(self, store_id: str, file_id: str) -> Dict[str, Any]:
        store = self._load_vector_store(store_id)
        for item in store.get("items", []):
            if item.get("file_id") == file_id:
                return self._vector_store_file_summary(store, item)
        raise FileNotFoundError(f"Unknown local vector store file: {file_id}")

    def vector_store_files_content(self, store_id: str, file_id: str) -> Dict[str, Any]:
        self.vector_store_files_retrieve(store_id, file_id)
        content, _content_type, record = self.files_content(file_id)
        return {
            "object": "list",
            "data": [{
                "type": "text",
                "text": content.decode("utf-8", errors="replace"),
            }],
            "oauth_compat_route": record.get("route"),
        }

    def vector_store_files_delete(self, store_id: str, file_id: str) -> Dict[str, Any]:
        store = self._load_vector_store(store_id)
        before = len(store.get("items", []))
        store["items"] = [item for item in store.get("items", []) if item.get("file_id") != file_id]
        if len(store["items"]) == before:
            raise FileNotFoundError(f"Unknown local vector store file: {file_id}")
        self._save_vector_store(store)
        return {
            "id": file_id,
            "object": "vector_store.file.deleted",
            "deleted": True,
            "oauth_compat_route": store.get("route"),
        }

    def vector_store_file_batches_create(
        self,
        store_id: str,
        file_ids: list[str],
        *,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not file_ids:
            raise ValueError("file_ids must contain at least one file id")
        batch_id = f"vsfb-local-{uuid.uuid4().hex}"
        completed_file_ids: list[str] = []
        for file_id in file_ids:
            if not isinstance(file_id, str) or not file_id:
                raise ValueError("file_ids must contain only non-empty strings")
            try:
                self.vector_store_files_retrieve(store_id, file_id)
            except FileNotFoundError:
                self.vector_store_files_create(store_id, file_id, attributes=attributes)
            completed_file_ids.append(file_id)
        store = self._load_vector_store(store_id)
        batch = {
            "id": batch_id,
            "object": "oauth_compat.vector_store.file_batch",
            "route": store.get("route"),
            "vector_store_id": store_id,
            "created_at": int(time.time()),
            "status": "completed",
            "file_ids": completed_file_ids,
        }
        store.setdefault("file_batches", []).append(batch)
        self._save_vector_store(store)
        return self._vector_store_file_batch_summary(batch)

    def vector_store_file_batches_retrieve(self, store_id: str, batch_id: str) -> Dict[str, Any]:
        batch = self._find_vector_store_file_batch(store_id, batch_id)
        return self._vector_store_file_batch_summary(batch)

    def vector_store_file_batches_cancel(self, store_id: str, batch_id: str) -> Dict[str, Any]:
        store = self._load_vector_store(store_id)
        for batch in store.get("file_batches", []):
            if batch.get("id") == batch_id:
                batch["status"] = "cancelled"
                self._save_vector_store(store)
                return self._vector_store_file_batch_summary(batch)
        raise FileNotFoundError(f"Unknown local vector store file batch: {batch_id}")

    def vector_store_file_batches_files_list(self, store_id: str, batch_id: str) -> Dict[str, Any]:
        batch = self._find_vector_store_file_batch(store_id, batch_id)
        data = []
        for file_id in batch.get("file_ids", []):
            try:
                data.append(self.vector_store_files_retrieve(store_id, str(file_id)))
            except FileNotFoundError:
                continue
        return {
            "object": "oauth_compat.list",
            "route": batch.get("route"),
            "data": data,
        }

    def _vector_stores_add_text(
        self,
        store_id: str,
        text: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        file_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        store = self._load_vector_store(store_id)
        vector = self._embedding_vector(text)
        item = {
            "id": f"vsi-local-{uuid.uuid4().hex}",
            "text": text,
            "metadata": metadata or {},
            "embedding": vector,
            "created_at": int(time.time()),
        }
        if file_id:
            item["file_id"] = file_id
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

    def fine_tuning_graders_validate(self, grader: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(grader, dict):
            raise ValueError("grader must be an object")
        valid, errors, warnings = self._validate_local_grader(grader)
        return {
            "object": "oauth_compat.fine_tuning.grader.validation",
            "route": "local_fine_tuning_grader",
            "grader": grader,
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "supported_local_grader_types": ["string_check", "multi"],
        }

    def fine_tuning_graders_run(
        self,
        grader: Dict[str, Any],
        *,
        model_sample: Any,
        item: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not isinstance(grader, dict):
            raise ValueError("grader must be an object")
        started = time.perf_counter()
        sample = self._normalize_grader_sample(model_sample)
        result = self._run_local_grader(grader, sample=sample, item=item or {})
        metadata = result.get("metadata", {})
        if isinstance(metadata, dict):
            metadata["execution_time"] = round(time.perf_counter() - started, 6)
            metadata["local"] = True
            metadata["oauth_compat_route"] = "local_fine_tuning_grader"
        return {
            "object": "oauth_compat.fine_tuning.grader.run",
            "route": "local_fine_tuning_grader",
            "reward": float(result.get("reward", 0.0)),
            "metadata": metadata,
            "sub_rewards": result.get("sub_rewards", {}),
            "model_grader_token_usage_per_model": {},
        }

    def fine_tuning_jobs_create(
        self,
        *,
        model: str,
        training_file: str,
        validation_file: Optional[str] = None,
        suffix: Optional[str] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
        integrations: Optional[List[Dict[str, Any]]] = None,
        seed: Optional[int] = None,
        method: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not model:
            raise ValueError("model must be a non-empty string")
        if not training_file:
            raise ValueError("training_file must be a non-empty string")
        now = int(time.time())
        job_id = f"ftjob-local-{uuid.uuid4().hex}"
        checkpoint_id = f"ftckpt-local-{uuid.uuid4().hex}"
        record = {
            "id": job_id,
            "object": "fine_tuning.job",
            "created_at": now,
            "finished_at": None,
            "model": model,
            "fine_tuned_model": None,
            "organization_id": "org-local-oauth-compat",
            "result_files": [],
            "status": "queued",
            "trained_tokens": None,
            "training_file": training_file,
            "validation_file": validation_file,
            "suffix": suffix,
            "hyperparameters": hyperparameters or {},
            "integrations": integrations or [],
            "seed": seed,
            "method": method or {},
            "metadata": metadata or {},
            "estimated_finish": None,
            "hosted_training_started": False,
            "route": "local_fine_tuning_job_store",
            "oauth_compat_route": "local_fine_tuning_job_store",
            "oauth_compat_note": (
                "Local metadata/lifecycle compatibility only; this does not start hosted "
                "OpenAI fine-tuning or create a hosted fine-tuned model."
            ),
            "events": [
                self._fine_tuning_event(
                    "message",
                    "Local fine-tuning job metadata created; hosted training was not started.",
                    created_at=now,
                )
            ],
            "checkpoints": [
                self._fine_tuning_checkpoint_shape(
                    checkpoint_id,
                    job_id=job_id,
                    model=model,
                    created_at=now,
                    step_number=0,
                )
            ],
        }
        self._save_fine_tuning_job(record)
        return self._fine_tuning_job_shape(record)

    def fine_tuning_jobs_list(self, *, limit: int = 100) -> Dict[str, Any]:
        records = [
            json.loads(path.read_text())
            for path in sorted(LOCAL_FINE_TUNING_JOBS.glob("ftjob-local-*.json"))
        ]
        records.sort(key=lambda item: int(item.get("created_at") or 0), reverse=True)
        data = [self._fine_tuning_job_shape(record) for record in records[: max(0, limit)]]
        return self._list_payload(data, route="local_fine_tuning_job_store")

    def fine_tuning_jobs_retrieve(self, job_id: str) -> Dict[str, Any]:
        return self._fine_tuning_job_shape(self._load_fine_tuning_job(job_id))

    def fine_tuning_jobs_cancel(self, job_id: str) -> Dict[str, Any]:
        return self._fine_tuning_jobs_transition(
            job_id,
            status="cancelled",
            message="Local fine-tuning job metadata marked cancelled; no hosted training was running.",
            finished=True,
        )

    def fine_tuning_jobs_pause(self, job_id: str) -> Dict[str, Any]:
        return self._fine_tuning_jobs_transition(
            job_id,
            status="paused",
            message="Local fine-tuning job metadata marked paused; no hosted training was running.",
        )

    def fine_tuning_jobs_resume(self, job_id: str) -> Dict[str, Any]:
        return self._fine_tuning_jobs_transition(
            job_id,
            status="queued",
            message="Local fine-tuning job metadata resumed to queued; hosted training was not started.",
        )

    def fine_tuning_job_events_list(self, job_id: str, *, limit: int = 100) -> Dict[str, Any]:
        record = self._load_fine_tuning_job(job_id)
        events = list(record.get("events") or [])
        events.sort(key=lambda item: int(item.get("created_at") or 0), reverse=True)
        return self._list_payload(events[: max(0, limit)], route="local_fine_tuning_job_store")

    def fine_tuning_job_checkpoints_list(self, job_id: str, *, limit: int = 100) -> Dict[str, Any]:
        record = self._load_fine_tuning_job(job_id)
        checkpoints = list(record.get("checkpoints") or [])
        checkpoints.sort(key=lambda item: int(item.get("created_at") or 0), reverse=True)
        return self._list_payload(checkpoints[: max(0, limit)], route="local_fine_tuning_job_store")

    def fine_tuning_checkpoint_permissions_list(self, checkpoint_id: str, *, limit: int = 100) -> Dict[str, Any]:
        permissions = []
        for path in sorted(self._fine_tuning_checkpoint_permissions_dir(checkpoint_id).glob("*.json")):
            permissions.append(json.loads(path.read_text()))
        permissions.sort(key=lambda item: int(item.get("created_at") or 0), reverse=True)
        return self._list_payload(permissions[: max(0, limit)], route="local_fine_tuning_checkpoint_permission_store")

    def fine_tuning_checkpoint_permissions_create(self, checkpoint_id: str, *, project_id: str) -> Dict[str, Any]:
        if not project_id:
            raise ValueError("project_id must be a non-empty string")
        permission = {
            "id": f"cp-local-{uuid.uuid4().hex}",
            "object": "checkpoint.permission",
            "created_at": int(time.time()),
            "project_id": project_id,
            "fine_tuned_model_checkpoint": checkpoint_id,
            "route": "local_fine_tuning_checkpoint_permission_store",
            "oauth_compat_route": "local_fine_tuning_checkpoint_permission_store",
            "hosted_permission_created": False,
        }
        self._save_fine_tuning_checkpoint_permission(checkpoint_id, permission)
        return permission

    def fine_tuning_checkpoint_permissions_delete(self, checkpoint_id: str, permission_id: str) -> Dict[str, Any]:
        path = self._fine_tuning_checkpoint_permission_path(checkpoint_id, permission_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local checkpoint permission: {permission_id}")
        path.unlink()
        return {
            "id": permission_id,
            "object": "checkpoint.permission.deleted",
            "deleted": True,
            "fine_tuned_model_checkpoint": checkpoint_id,
            "oauth_compat_route": "local_fine_tuning_checkpoint_permission_store",
            "hosted_permission_deleted": False,
        }

    def evals_create(
        self,
        *,
        name: str,
        data_source_config: Dict[str, Any],
        testing_criteria: list[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        eval_id = f"eval-local-{uuid.uuid4().hex}"
        record = {
            "id": eval_id,
            "object": "oauth_compat.eval",
            "route": "local_eval_plus_codex_text",
            "name": name,
            "created_at": int(time.time()),
            "data_source_config": data_source_config,
            "testing_criteria": testing_criteria,
            "metadata": metadata or {},
            "runs": [],
        }
        self._save_eval(record)
        return self._eval_summary(record)

    def evals_list(self) -> Dict[str, Any]:
        data = []
        for path in sorted(LOCAL_EVALS.glob("eval-local-*.json")):
            data.append(self._eval_summary(json.loads(path.read_text())))
        return {"object": "oauth_compat.list", "route": "local_eval_plus_codex_text", "data": data}

    def evals_retrieve(self, eval_id: str) -> Dict[str, Any]:
        return self._eval_summary(self._load_eval(eval_id))

    def evals_update(self, eval_id: str, *, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        record = self._load_eval(eval_id)
        if name:
            record["name"] = name
        if metadata is not None:
            record["metadata"] = metadata
        self._save_eval(record)
        return self._eval_summary(record)

    def evals_delete(self, eval_id: str) -> Dict[str, Any]:
        self._load_eval(eval_id)
        self._eval_path(eval_id).unlink(missing_ok=True)
        return {"eval_id": eval_id, "object": "eval.deleted", "deleted": True}

    def eval_runs_create(
        self,
        eval_id: str,
        *,
        name: str,
        data_source: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        record = self._load_eval(eval_id)
        prompt, expected = self._extract_eval_case(data_source, metadata or {}, record.get("metadata", {}))
        result = self.eval_text_expectation(prompt, expected)
        output_item_id = f"evaloi-local-{uuid.uuid4().hex}"
        passed = bool(result.get("passed"))
        run_id = f"evalrun-local-{uuid.uuid4().hex}"
        output_item = {
            "id": output_item_id,
            "object": "oauth_compat.eval.run.output_item",
            "created_at": int(time.time()),
            "eval_id": eval_id,
            "run_id": run_id,
            "status": "pass" if passed else "fail",
            "datasource_item_id": "local-item-0",
            "datasource_item": {
                "prompt": prompt,
                "expected_substring": expected,
            },
            "sample": {
                "output_text": result.get("output_text"),
            },
            "results": [{
                "name": "expected_substring",
                "passed": passed,
                "expected": expected,
            }],
        }
        run = {
            "id": run_id,
            "object": "oauth_compat.eval.run",
            "route": "local_eval_plus_codex_text",
            "created_at": int(time.time()),
            "eval_id": eval_id,
            "name": name,
            "metadata": metadata or {},
            "data_source": data_source,
            "status": "completed",
            "model": self.oauth.text_model,
            "error": None,
            "report_url": None,
            "per_model_usage": [],
            "per_testing_criteria_results": [],
            "result_counts": {
                "total": 1,
                "errored": 0,
                "failed": 0 if passed else 1,
                "passed": 1 if passed else 0,
            },
            "output_items": [output_item],
        }
        record.setdefault("runs", []).append(run)
        self._save_eval(record)
        return self._eval_run_summary(run)

    def eval_runs_list(self, eval_id: str) -> Dict[str, Any]:
        record = self._load_eval(eval_id)
        return {
            "object": "oauth_compat.list",
            "route": "local_eval_plus_codex_text",
            "data": [self._eval_run_summary(run) for run in record.get("runs", [])],
        }

    def eval_runs_retrieve(self, eval_id: str, run_id: str) -> Dict[str, Any]:
        return self._eval_run_summary(self._find_eval_run(eval_id, run_id))

    def eval_runs_cancel(self, eval_id: str, run_id: str) -> Dict[str, Any]:
        record = self._load_eval(eval_id)
        for run in record.get("runs", []):
            if run.get("id") == run_id:
                run["status"] = "canceled"
                self._save_eval(record)
                return self._eval_run_summary(run)
        raise FileNotFoundError(f"Unknown local eval run: {run_id}")

    def eval_runs_delete(self, eval_id: str, run_id: str) -> Dict[str, Any]:
        record = self._load_eval(eval_id)
        before = len(record.get("runs", []))
        record["runs"] = [run for run in record.get("runs", []) if run.get("id") != run_id]
        if len(record["runs"]) == before:
            raise FileNotFoundError(f"Unknown local eval run: {run_id}")
        self._save_eval(record)
        return {"run_id": run_id, "object": "eval.run.deleted", "deleted": True}

    def eval_output_items_list(self, eval_id: str, run_id: str) -> Dict[str, Any]:
        run = self._find_eval_run(eval_id, run_id)
        return {
            "object": "oauth_compat.list",
            "route": "local_eval_plus_codex_text",
            "data": [self._eval_output_item_shape(item) for item in run.get("output_items", [])],
        }

    def eval_output_items_retrieve(self, eval_id: str, run_id: str, output_item_id: str) -> Dict[str, Any]:
        run = self._find_eval_run(eval_id, run_id)
        for item in run.get("output_items", []):
            if item.get("id") == output_item_id:
                return self._eval_output_item_shape(item)
        raise FileNotFoundError(f"Unknown local eval output item: {output_item_id}")

    def organization_sandbox(
        self,
        path: str,
        *,
        method: str = "GET",
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized = self._normalize_openai_path(path)
        parts = [part for part in normalized.split("/") if part]
        if not parts or parts[0] not in {"organization", "projects"}:
            raise FileNotFoundError(f"Unsupported local organization sandbox path: {path}")
        method = method.upper()
        context = self._organization_context(parts)
        if parts[:2] == ["organization", "usage"] and len(parts) >= 3:
            return self._organization_usage_shape(parts[2], context=context)
        if normalized == "/organization/costs":
            return self._organization_costs_shape(context=context)
        if normalized.endswith("/data_retention"):
            return self._organization_data_retention_shape(context=context)
        if method == "DELETE":
            return self._organization_delete_shape(parts, context=context)
        if method == "POST" and parts[-1] in {"activate", "deactivate", "archive"}:
            return self._organization_action_shape(parts, action=parts[-1], context=context, body=body or {})
        resource_key, is_collection = self._organization_resource_key(parts)
        if is_collection:
            return self._organization_list_shape(resource_key, context=context)
        return self._organization_resource_shape(resource_key, resource_id=parts[-1], context=context)

    def videos_create(
        self,
        *,
        prompt: str,
        model: Optional[str] = None,
        size: Optional[str] = None,
        seconds: Optional[str] = None,
        quality: Optional[str] = None,
        operation: str = "create",
        source_video_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not prompt:
            raise ValueError("prompt must be a non-empty string")
        now = int(time.time())
        video_id = f"video-local-{uuid.uuid4().hex}"
        record = {
            "id": video_id,
            "object": "video",
            "created_at": now,
            "completed_at": now,
            "status": "completed",
            "model": model or "sora-local-storyboard",
            "prompt": prompt,
            "size": size or "1280x720",
            "seconds": seconds or "4",
            "quality": quality or "standard",
            "operation": operation,
            "source_video_id": source_video_id,
            "metadata": metadata or {},
            "progress": 100,
            "route": "local_video_storyboard_sandbox",
            "oauth_compat_route": "local_video_storyboard_sandbox",
            "hosted_video_created": False,
            "local_video_rendered": False,
            "content_type": "application/json",
            "storyboard": [
                {
                    "index": 0,
                    "description": prompt,
                    "duration_seconds": seconds or "4",
                }
            ],
            "oauth_compat_note": (
                "Local storyboard/job metadata only; this does not render hosted Sora video "
                "or produce OpenAI-hosted MP4 bytes."
            ),
        }
        self._save_video(record)
        return self._video_shape(record)

    def videos_list(self, *, limit: int = 100) -> Dict[str, Any]:
        records = [
            json.loads(path.read_text())
            for path in sorted(LOCAL_VIDEOS.glob("video-local-*.json"))
        ]
        records.sort(key=lambda item: int(item.get("created_at") or 0), reverse=True)
        return self._list_payload(
            [self._video_shape(record) for record in records[: max(0, limit)]],
            route="local_video_storyboard_sandbox",
        )

    def videos_retrieve(self, video_id: str) -> Dict[str, Any]:
        return self._video_shape(self._load_video(video_id))

    def videos_delete(self, video_id: str) -> Dict[str, Any]:
        self._load_video(video_id)
        self._video_path(video_id).unlink(missing_ok=True)
        return {
            "id": video_id,
            "object": "video.deleted",
            "deleted": True,
            "oauth_compat_route": "local_video_storyboard_sandbox",
            "hosted_video_deleted": False,
        }

    def videos_remix(self, video_id: str, *, prompt: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        source = self._load_video(video_id)
        remix_prompt = prompt or f"Remix local storyboard for {source.get('prompt')}"
        return self.videos_create(
            prompt=remix_prompt,
            model=str(source.get("model") or "sora-local-storyboard"),
            size=str(source.get("size") or "1280x720"),
            seconds=str(source.get("seconds") or "4"),
            quality=str(source.get("quality") or "standard"),
            operation="remix",
            source_video_id=video_id,
            metadata=metadata,
        )

    def videos_content(self, video_id: str) -> tuple[bytes, str]:
        record = self._load_video(video_id)
        payload = {
            "id": video_id,
            "object": "video.local_content_manifest",
            "video": self._video_shape(record),
            "storyboard": record.get("storyboard") or [],
            "hosted_video_bytes": False,
            "oauth_compat_route": "local_video_storyboard_sandbox",
            "oauth_compat_note": "This is a local JSON storyboard manifest, not an MP4 render.",
        }
        return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8"), "application/json"

    def video_characters_list(self, *, limit: int = 100) -> Dict[str, Any]:
        records = [self._video_character_shape()]
        for path in sorted(LOCAL_VIDEO_CHARACTERS.glob("*.json")):
            records.append(json.loads(path.read_text()))
        return self._list_payload(records[: max(0, limit)], route="local_video_storyboard_sandbox")

    def video_characters_retrieve(self, character_id: str) -> Dict[str, Any]:
        if character_id == "vchar-local-default":
            return self._video_character_shape()
        path = LOCAL_VIDEO_CHARACTERS / f"{character_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Unknown local video character: {character_id}")
        return json.loads(path.read_text())

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

    def _eval_path(self, eval_id: str) -> Path:
        return LOCAL_EVALS / f"{eval_id}.json"

    def _file_metadata_path(self, file_id: str) -> Path:
        return LOCAL_FILES / file_id / "metadata.json"

    def _container_dir(self, container_id: str) -> Path:
        return LOCAL_CONTAINERS / container_id

    def _container_metadata_path(self, container_id: str) -> Path:
        return self._container_dir(container_id) / "metadata.json"

    def _container_files_dir(self, container_id: str) -> Path:
        return self._container_dir(container_id) / "files"

    def _container_file_metadata_path(self, container_id: str, file_id: str) -> Path:
        return self._container_files_dir(container_id) / f"{file_id}.metadata.json"

    def _upload_path(self, upload_id: str) -> Path:
        return LOCAL_UPLOADS / upload_id / "metadata.json"

    def _upload_parts_dir(self, upload_id: str) -> Path:
        return LOCAL_UPLOADS / upload_id / "parts"

    def _batch_path(self, batch_id: str) -> Path:
        return LOCAL_BATCHES / f"{batch_id}.json"

    def _response_path(self, response_id: str) -> Path:
        return LOCAL_RESPONSES / f"{response_id}.json"

    def _chat_completion_path(self, completion_id: str) -> Path:
        return LOCAL_CHAT_COMPLETIONS / f"{completion_id}.json"

    def _assistant_path(self, assistant_id: str) -> Path:
        return LOCAL_ASSISTANTS / f"{assistant_id}.json"

    def _thread_path(self, thread_id: str) -> Path:
        return LOCAL_THREADS / f"{thread_id}.json"

    def _conversation_path(self, conversation_id: str) -> Path:
        return LOCAL_CONVERSATIONS / f"{conversation_id}.json"

    def _realtime_call_path(self, call_id: str) -> Path:
        safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", call_id).strip("-") or "call"
        return LOCAL_REALTIME_CALLS / f"{safe_id}.json"

    def _audio_voice_consent_path(self, consent_id: str) -> Path:
        return LOCAL_AUDIO_VOICE_CONSENTS / consent_id / "metadata.json"

    def _audio_voice_path(self, voice_id: str) -> Path:
        return LOCAL_AUDIO_VOICES / f"{voice_id}.json"

    def _audio_builtin_voice_shape(self, voice_id: str) -> Dict[str, Any]:
        return {
            "id": voice_id,
            "object": "audio.voice",
            "created_at": None,
            "name": voice_id,
            "type": "built_in",
            "route": "local_audio_voice_catalog",
            "oauth_compat_route": "local_audio_voice_catalog",
            "hosted_voice_created": True,
        }

    def _fine_tuning_job_path(self, job_id: str) -> Path:
        return LOCAL_FINE_TUNING_JOBS / f"{job_id}.json"

    def _fine_tuning_checkpoint_permissions_dir(self, checkpoint_id: str) -> Path:
        safe_id = hashlib.sha256(checkpoint_id.encode("utf-8")).hexdigest()
        return LOCAL_FINE_TUNING_PERMISSIONS / safe_id

    def _fine_tuning_checkpoint_permission_path(self, checkpoint_id: str, permission_id: str) -> Path:
        safe_permission_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", permission_id).strip("-") or "permission"
        return self._fine_tuning_checkpoint_permissions_dir(checkpoint_id) / f"{safe_permission_id}.json"

    def _load_fine_tuning_job(self, job_id: str) -> Dict[str, Any]:
        path = self._fine_tuning_job_path(job_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local fine-tuning job: {job_id}")
        return json.loads(path.read_text())

    def _save_fine_tuning_job(self, record: Dict[str, Any]) -> None:
        self._fine_tuning_job_path(record["id"]).write_text(json.dumps(record, indent=2, sort_keys=True))

    def _save_fine_tuning_checkpoint_permission(self, checkpoint_id: str, permission: Dict[str, Any]) -> None:
        directory = self._fine_tuning_checkpoint_permissions_dir(checkpoint_id)
        directory.mkdir(parents=True, exist_ok=True)
        self._fine_tuning_checkpoint_permission_path(checkpoint_id, permission["id"]).write_text(
            json.dumps(permission, indent=2, sort_keys=True)
        )

    def _fine_tuning_event(
        self,
        level: str,
        message: str,
        *,
        created_at: Optional[int] = None,
    ) -> Dict[str, Any]:
        return {
            "id": f"ftevent-local-{uuid.uuid4().hex}",
            "object": "fine_tuning.job.event",
            "created_at": created_at or int(time.time()),
            "level": level,
            "message": message,
            "type": level,
            "data": {},
            "oauth_compat_route": "local_fine_tuning_job_store",
        }

    def _fine_tuning_checkpoint_shape(
        self,
        checkpoint_id: str,
        *,
        job_id: str,
        model: str,
        created_at: int,
        step_number: int,
    ) -> Dict[str, Any]:
        return {
            "id": checkpoint_id,
            "object": "fine_tuning.job.checkpoint",
            "created_at": created_at,
            "fine_tuned_model_checkpoint": checkpoint_id,
            "fine_tuning_job_id": job_id,
            "metrics": {
                "step": step_number,
                "train_loss": None,
                "train_mean_token_accuracy": None,
                "valid_loss": None,
                "valid_mean_token_accuracy": None,
            },
            "step_number": step_number,
            "model": model,
            "hosted_checkpoint_created": False,
            "oauth_compat_route": "local_fine_tuning_job_store",
        }

    def _fine_tuning_job_shape(self, record: Dict[str, Any]) -> Dict[str, Any]:
        fields = [
            "id",
            "object",
            "created_at",
            "finished_at",
            "model",
            "fine_tuned_model",
            "organization_id",
            "result_files",
            "status",
            "trained_tokens",
            "training_file",
            "validation_file",
            "suffix",
            "hyperparameters",
            "integrations",
            "seed",
            "method",
            "metadata",
            "estimated_finish",
            "hosted_training_started",
            "oauth_compat_route",
            "oauth_compat_note",
        ]
        return {key: record.get(key) for key in fields if key in record}

    def _fine_tuning_jobs_transition(
        self,
        job_id: str,
        *,
        status: str,
        message: str,
        finished: bool = False,
    ) -> Dict[str, Any]:
        record = self._load_fine_tuning_job(job_id)
        record["status"] = status
        if finished:
            record["finished_at"] = int(time.time())
        events = record.get("events")
        if not isinstance(events, list):
            events = []
        events.append(self._fine_tuning_event("message", message))
        record["events"] = events
        self._save_fine_tuning_job(record)
        return self._fine_tuning_job_shape(record)

    def _normalize_openai_path(self, path: str) -> str:
        normalized = "/" + "/".join(part for part in path.split("/") if part)
        if normalized.startswith("/v1/"):
            normalized = normalized[3:]
        return normalized

    def _organization_context(self, parts: List[str]) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "organization_id": "org-local-oauth-compat",
            "project_id": "proj-local-default",
            "group_id": "group-local-developers",
            "user_id": "user-local-owner",
        }
        for index, part in enumerate(parts[:-1]):
            next_part = parts[index + 1]
            if part == "projects" and not next_part.startswith("{") and next_part not in ORG_COLLECTION_KEYS:
                context["project_id"] = next_part
            elif part == "groups" and not next_part.startswith("{") and next_part not in ORG_COLLECTION_KEYS:
                context["group_id"] = next_part
            elif part == "users" and not next_part.startswith("{") and next_part not in ORG_COLLECTION_KEYS:
                context["user_id"] = next_part
        return context

    def _organization_resource_key(self, parts: List[str]) -> tuple[str, bool]:
        tail = parts[-1]
        if tail in ORG_COLLECTION_KEYS:
            return tail, True
        if len(parts) >= 2 and parts[-2] in ORG_COLLECTION_KEYS:
            return parts[-2], False
        return tail, False

    def _organization_list_shape(self, resource_key: str, *, context: Dict[str, Any]) -> Dict[str, Any]:
        return self._list_payload(
            [self._organization_resource_shape(resource_key, context=context)],
            route="local_organization_project_sandbox",
        )

    def _organization_resource_shape(
        self,
        resource_key: str,
        *,
        resource_id: Optional[str] = None,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = int(time.time())
        defaults = {
            "admin_api_keys": "key-local-admin",
            "api_keys": "key-local-project",
            "audit_logs": "audit-local-boot",
            "certificates": "cert-local-dev",
            "groups": context.get("group_id") or "group-local-developers",
            "hosted_tool_permissions": "htp-local-default",
            "invites": "invite-local-dev",
            "model_permissions": "mp-local-default",
            "projects": context.get("project_id") or "proj-local-default",
            "rate_limits": "rl-local-default",
            "roles": "role-local-admin",
            "service_accounts": "svcacct-local-dev",
            "spend_alerts": "alert-local-dev",
            "users": context.get("user_id") or "user-local-owner",
        }
        object_names = {
            "admin_api_keys": "organization.admin_api_key",
            "api_keys": "organization.project.api_key",
            "audit_logs": "organization.audit_log",
            "certificates": "organization.certificate",
            "groups": "organization.group",
            "hosted_tool_permissions": "organization.project.hosted_tool_permission",
            "invites": "organization.invite",
            "model_permissions": "organization.project.model_permission",
            "projects": "organization.project",
            "rate_limits": "organization.project.rate_limit",
            "roles": "organization.role",
            "service_accounts": "organization.project.service_account",
            "spend_alerts": "organization.spend_alert",
            "users": "organization.user",
        }
        item_id = resource_id or defaults.get(resource_key) or f"{resource_key.rstrip('s')}-local-default"
        item: Dict[str, Any] = {
            "id": item_id,
            "object": object_names.get(resource_key, f"organization.{resource_key}"),
            "created_at": now,
            "organization_id": context.get("organization_id"),
            "project_id": context.get("project_id"),
            "oauth_compat_route": "local_organization_project_sandbox",
            "hosted_admin_resource": False,
            "oauth_compat_note": "Local sandbox metadata only; real organization/project data and mutations require OpenAI Admin/API credentials.",
        }
        if resource_key == "projects":
            item.update({"name": "Local OAuth Compatibility Project", "status": "active", "archived_at": None})
        elif resource_key == "users":
            item.update({"name": "Local OAuth User", "email": "local-user@example.invalid", "role": "owner"})
        elif resource_key == "roles":
            item.update({"name": "Local admin", "permissions": ["local:sandbox"]})
        elif resource_key == "groups":
            item.update({"name": "Local Developers", "description": "Local organization/project sandbox group"})
        elif resource_key in {"admin_api_keys", "api_keys"}:
            item.update({"name": "local-sandbox-key", "redacted_value": "sk-local-...sandbox", "owner": "local"})
        elif resource_key == "audit_logs":
            item.update({"type": "local_sandbox.event", "actor": {"id": "user-local-owner"}, "data": {}})
        elif resource_key == "certificates":
            item.update({"name": "local-sandbox-certificate", "active": True})
        elif resource_key == "invites":
            item.update({"email": "invitee@example.invalid", "status": "pending"})
        elif resource_key == "spend_alerts":
            item.update({"name": "Local spend alert", "threshold": 0, "status": "enabled"})
        elif resource_key == "rate_limits":
            item.update({"model": self.oauth.text_model, "max_requests_per_1_minute": 0, "max_tokens_per_1_minute": 0})
        elif resource_key == "service_accounts":
            item.update({"name": "local-service-account", "role": "owner"})
        elif resource_key == "model_permissions":
            item.update({"model": self.oauth.text_model, "enabled": True})
        elif resource_key == "hosted_tool_permissions":
            item.update({"tool": "local-sandbox", "enabled": True})
        return item

    def _organization_usage_shape(self, metric: str, *, context: Dict[str, Any]) -> Dict[str, Any]:
        if metric not in ORG_USAGE_METRICS:
            raise FileNotFoundError(f"Unsupported local organization usage metric: {metric}")
        return {
            "object": f"organization.usage.{metric}.result",
            "data": [],
            "has_more": False,
            "bucket_width": "1d",
            "start_time": None,
            "end_time": None,
            "organization_id": context.get("organization_id"),
            "oauth_compat_route": "local_organization_usage_sandbox",
            "hosted_usage_report": False,
            "oauth_compat_note": "Local sandbox report only; real organization usage requires OpenAI Admin credentials.",
        }

    def _organization_costs_shape(self, *, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "object": "organization.costs.result",
            "data": [],
            "has_more": False,
            "organization_id": context.get("organization_id"),
            "oauth_compat_route": "local_organization_usage_sandbox",
            "hosted_cost_report": False,
            "oauth_compat_note": "Local sandbox report only; real organization costs require OpenAI Admin credentials.",
        }

    def _organization_data_retention_shape(self, *, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "object": "organization.data_retention",
            "organization_id": context.get("organization_id"),
            "project_id": context.get("project_id"),
            "retention_days": None,
            "zero_data_retention": False,
            "oauth_compat_route": "local_organization_project_sandbox",
            "hosted_admin_resource": False,
            "oauth_compat_note": "Local sandbox metadata only; real data-retention settings require OpenAI Admin credentials.",
        }

    def _organization_action_shape(
        self,
        parts: List[str],
        *,
        action: str,
        context: Dict[str, Any],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = int(time.time())
        if action == "archive":
            project_id = context.get("project_id") or (parts[-2] if len(parts) >= 2 else "proj-local-default")
            project = self._organization_resource_shape("projects", resource_id=str(project_id), context=context)
            project.update({"status": "archived", "archived_at": now})
            return project
        certificate_id = body.get("certificate_id") if isinstance(body.get("certificate_id"), str) else "cert-local-dev"
        certificate = self._organization_resource_shape("certificates", resource_id=certificate_id, context=context)
        certificate.update({
            "active": action == "activate",
            "status": "active" if action == "activate" else "inactive",
            "action": action,
            "hosted_admin_resource_mutated": False,
        })
        return certificate

    def _organization_delete_shape(self, parts: List[str], *, context: Dict[str, Any]) -> Dict[str, Any]:
        resource_key, _is_collection = self._organization_resource_key(parts)
        deleted_id = parts[-1] if parts else resource_key
        return {
            "id": deleted_id,
            "object": f"{resource_key.rstrip('s')}.deleted",
            "deleted": True,
            "organization_id": context.get("organization_id"),
            "project_id": context.get("project_id"),
            "oauth_compat_route": "local_organization_project_sandbox",
            "hosted_admin_resource_deleted": False,
        }

    def _video_path(self, video_id: str) -> Path:
        return LOCAL_VIDEOS / f"{video_id}.json"

    def _load_video(self, video_id: str) -> Dict[str, Any]:
        path = self._video_path(video_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local video: {video_id}")
        return json.loads(path.read_text())

    def _save_video(self, record: Dict[str, Any]) -> None:
        self._video_path(record["id"]).write_text(json.dumps(record, indent=2, sort_keys=True))

    def _video_shape(self, record: Dict[str, Any]) -> Dict[str, Any]:
        fields = [
            "id",
            "object",
            "created_at",
            "completed_at",
            "status",
            "model",
            "prompt",
            "size",
            "seconds",
            "quality",
            "operation",
            "source_video_id",
            "metadata",
            "progress",
            "content_type",
            "hosted_video_created",
            "local_video_rendered",
            "oauth_compat_route",
            "oauth_compat_note",
        ]
        return {key: record.get(key) for key in fields if key in record}

    def _video_character_shape(self) -> Dict[str, Any]:
        return {
            "id": "vchar-local-default",
            "object": "video.character",
            "created_at": None,
            "name": "Local storyboard character",
            "description": "Reusable local-only character metadata for video storyboard compatibility.",
            "metadata": {},
            "hosted_character": False,
            "oauth_compat_route": "local_video_storyboard_sandbox",
        }

    def _list_payload(self, data: List[Dict[str, Any]], *, route: str) -> Dict[str, Any]:
        return {
            "object": "list",
            "data": data,
            "first_id": data[0]["id"] if data else None,
            "last_id": data[-1]["id"] if data else None,
            "has_more": False,
            "oauth_compat_route": route,
        }

    def _chatkit_session_path(self, session_id: str) -> Path:
        return LOCAL_CHATKIT / "sessions" / f"{session_id}.json"

    def _chatkit_thread_path(self, thread_id: str) -> Path:
        return LOCAL_CHATKIT / "threads" / f"{thread_id}.json"

    def _local_skill_dir(self, skill_id: str) -> Path:
        return LOCAL_SKILLS / "local" / skill_id

    def _local_skill_metadata_path(self, skill_id: str) -> Path:
        return self._local_skill_dir(skill_id) / "metadata.json"

    def _load_vector_store(self, store_id: str) -> Dict[str, Any]:
        path = self._vector_path(store_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local vector store: {store_id}")
        return json.loads(path.read_text())

    def _save_vector_store(self, store: Dict[str, Any]) -> None:
        self._vector_path(store["id"]).write_text(json.dumps(store, indent=2, sort_keys=True))

    def _load_container(self, container_id: str) -> Dict[str, Any]:
        path = self._container_metadata_path(container_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local container: {container_id}")
        return json.loads(path.read_text())

    def _save_container(self, container: Dict[str, Any]) -> None:
        self._container_dir(container["id"]).mkdir(parents=True, exist_ok=True)
        self._container_metadata_path(container["id"]).write_text(json.dumps(container, indent=2, sort_keys=True))

    def _load_chatkit_session(self, session_id: str) -> Dict[str, Any]:
        path = self._chatkit_session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local ChatKit session: {session_id}")
        return json.loads(path.read_text())

    def _save_chatkit_session(self, session: Dict[str, Any]) -> None:
        self._chatkit_session_path(session["id"]).write_text(json.dumps(session, indent=2, sort_keys=True))

    def _load_chatkit_thread(self, thread_id: str) -> Dict[str, Any]:
        path = self._chatkit_thread_path(thread_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local ChatKit thread: {thread_id}")
        return json.loads(path.read_text())

    def _save_chatkit_thread(self, thread: Dict[str, Any]) -> None:
        self._chatkit_thread_path(thread["id"]).write_text(json.dumps(thread, indent=2, sort_keys=True))

    def _skills_registry(self) -> Dict[str, Dict[str, Any]]:
        records: Dict[str, Dict[str, Any]] = {}
        for path in sorted((LOCAL_SKILLS / "local").glob("*/metadata.json")):
            try:
                record = json.loads(path.read_text())
            except Exception:
                continue
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                records[record["id"]] = record
        for record in self._installed_skill_records():
            records.setdefault(record["id"], record)
        return records

    def _installed_skill_records(self) -> List[Dict[str, Any]]:
        codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
        roots = [codex_home / "skills", codex_home / "plugins" / "cache"]
        records: List[Dict[str, Any]] = []
        for root in roots:
            if not root.exists():
                continue
            for skill_md in sorted(root.rglob("SKILL.md"))[:500]:
                skill_dir = skill_md.parent
                try:
                    text = skill_md.read_text(encoding="utf-8", errors="replace")
                    stat = skill_md.stat()
                except Exception:
                    continue
                meta = self._parse_skill_frontmatter(text)
                name = meta.get("name") or skill_dir.name
                description = meta.get("description") or ""
                key = str(skill_dir)
                skill_id = f"skill-installed-{self._safe_slug(name)}-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:12]}"
                version = f"local-{hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]}"
                records.append({
                    "id": skill_id,
                    "object": "skill",
                    "created_at": int(stat.st_mtime),
                    "name": name,
                    "description": description,
                    "default_version": version,
                    "latest_version": version,
                    "metadata": {
                        "source": "installed_codex_skill",
                        "root": str(root),
                    },
                    "source": "installed_codex_skill",
                    "read_only": True,
                    "skill_dir": str(skill_dir),
                    "route": "local_skill_registry",
                })
        return records

    def _load_skill_record(self, skill_id: str) -> Dict[str, Any]:
        record = self._skills_registry().get(skill_id)
        if not record:
            raise FileNotFoundError(f"Unknown local skill: {skill_id}")
        return record

    def _save_local_skill_metadata(self, record: Dict[str, Any]) -> None:
        if not isinstance(record.get("id"), str):
            raise ValueError("skill record must include id")
        self._local_skill_dir(record["id"]).mkdir(parents=True, exist_ok=True)
        self._local_skill_metadata_path(record["id"]).write_text(json.dumps(record, indent=2, sort_keys=True))

    def _require_writable_skill(self, record: Dict[str, Any]) -> None:
        if record.get("read_only"):
            raise ValueError("installed Codex skills are read-only through this compatibility server")

    def _skill_shape(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": record.get("id"),
            "object": "skill",
            "created_at": record.get("created_at"),
            "name": record.get("name"),
            "description": record.get("description") or "",
            "default_version": record.get("default_version"),
            "latest_version": record.get("latest_version"),
            "metadata": record.get("metadata") if isinstance(record.get("metadata"), dict) else {},
            "read_only": bool(record.get("read_only")),
            "source": record.get("source"),
            "oauth_compat_route": record.get("route") or "local_skill_registry",
        }

    def _skill_versions(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        if record.get("read_only"):
            return [self._skill_version_shape(record, str(record.get("default_version") or "local"))]
        versions_root = self._local_skill_dir(str(record["id"])) / "versions"
        return [
            self._skill_version_shape(record, path.name)
            for path in sorted(versions_root.iterdir())
            if path.is_dir()
        ]

    def _skill_version_shape(self, record: Dict[str, Any], version: str) -> Dict[str, Any]:
        version_dir = self._skill_version_dir(record, version)
        created_at = record.get("created_at")
        skill_md = version_dir / "SKILL.md"
        if skill_md.exists():
            created_at = int(skill_md.stat().st_mtime)
        return {
            "id": self._skill_version_id(str(record.get("id")), version),
            "object": "skill.version",
            "skill_id": record.get("id"),
            "version": version,
            "created_at": created_at,
            "metadata": {
                "source": record.get("source"),
                "read_only": bool(record.get("read_only")),
            },
            "oauth_compat_route": "local_skill_registry",
        }

    def _skill_version_id(self, skill_id: str, version: str) -> str:
        digest = hashlib.sha256(f"{skill_id}:{version}".encode("utf-8")).hexdigest()[:16]
        return f"skillver-local-{digest}"

    def _skill_version_dir(self, record: Dict[str, Any], version: str) -> Path:
        if record.get("read_only"):
            if version != str(record.get("default_version") or ""):
                return Path("__missing_read_only_skill_version__")
            return Path(str(record.get("skill_dir") or ""))
        return self._local_skill_dir(str(record["id"])) / "versions" / version

    def _write_skill_version_dir(
        self,
        version_dir: Path,
        *,
        name: str,
        description: Optional[str],
        content: Optional[str],
        bundle_bytes: Optional[bytes],
        filename: Optional[str],
    ) -> None:
        if bundle_bytes:
            self._extract_skill_bundle(bundle_bytes, version_dir, filename=filename)
        if not (version_dir / "SKILL.md").exists():
            (version_dir / "SKILL.md").write_text(
                self._skill_markdown(name=name, description=description, content=content),
                encoding="utf-8",
            )

    def _extract_skill_bundle(self, data: bytes, target_dir: Path, *, filename: Optional[str]) -> None:
        buffer = io.BytesIO(data)
        if zipfile.is_zipfile(buffer):
            buffer.seek(0)
            with zipfile.ZipFile(buffer) as archive:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    rel = PurePosixPath(info.filename)
                    if rel.is_absolute() or ".." in rel.parts:
                        continue
                    output = target_dir.joinpath(*rel.parts)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(archive.read(info))
            return
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename or "SKILL.md").name) or "SKILL.md"
        (target_dir / safe_name).write_bytes(data)

    def _zip_skill_dir(self, skill_dir: Path) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(skill_dir.rglob("*")):
                if path.is_dir() or any(part in {".git", "__pycache__"} for part in path.parts):
                    continue
                archive.write(path, path.relative_to(skill_dir).as_posix())
        return buffer.getvalue()

    def _parse_skill_frontmatter(self, text: str) -> Dict[str, str]:
        if not text.startswith("---"):
            return {}
        lines = text.splitlines()
        end = None
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                end = index
                break
        if end is None:
            return {}
        meta: Dict[str, str] = {}
        for line in lines[1:end]:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            if key in {"name", "description"} and value:
                meta[key] = value
        return meta

    def _skill_markdown(self, *, name: str, description: Optional[str], content: Optional[str]) -> str:
        if content and content.lstrip().startswith("---"):
            return content if content.endswith("\n") else content + "\n"
        body = (content or description or "Local compatibility skill created through the OAuth bridge.").strip()
        safe_name = name.replace('"', "'")
        safe_description = (description or body.splitlines()[0]).replace('"', "'")
        return "\n".join([
            "---",
            f"name: \"{safe_name}\"",
            f"description: \"{safe_description}\"",
            "---",
            "",
            body,
            "",
        ])

    def _safe_slug(self, value: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", value.lower()).strip("-")
        return slug[:48] or "skill"

    def _load_eval(self, eval_id: str) -> Dict[str, Any]:
        path = self._eval_path(eval_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local eval: {eval_id}")
        return json.loads(path.read_text())

    def _save_eval(self, record: Dict[str, Any]) -> None:
        self._eval_path(record["id"]).write_text(json.dumps(record, indent=2, sort_keys=True))

    def _load_upload(self, upload_id: str) -> Dict[str, Any]:
        path = self._upload_path(upload_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local upload: {upload_id}")
        return json.loads(path.read_text())

    def _save_upload(self, record: Dict[str, Any]) -> None:
        path = self._upload_path(record["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, sort_keys=True))

    def _load_batch(self, batch_id: str) -> Dict[str, Any]:
        path = self._batch_path(batch_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local batch: {batch_id}")
        return json.loads(path.read_text())

    def _save_batch(self, record: Dict[str, Any]) -> None:
        self._batch_path(record["id"]).write_text(json.dumps(record, indent=2, sort_keys=True))

    def _load_response(self, response_id: str) -> Dict[str, Any]:
        path = self._response_path(response_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local response: {response_id}")
        return json.loads(path.read_text())

    def _save_response(self, record: Dict[str, Any]) -> None:
        response_id = str(record.get("payload", {}).get("id") or "")
        if not response_id:
            raise ValueError("response payload must include id")
        self._response_path(response_id).write_text(json.dumps(record, indent=2, sort_keys=True))

    def _load_chat_completion(self, completion_id: str) -> Dict[str, Any]:
        path = self._chat_completion_path(completion_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local chat completion: {completion_id}")
        return json.loads(path.read_text())

    def _save_chat_completion(self, record: Dict[str, Any], completion_id: str) -> None:
        if not completion_id:
            raise ValueError("chat completion payload must include id")
        self._chat_completion_path(completion_id).write_text(json.dumps(record, indent=2, sort_keys=True))

    def _load_assistant(self, assistant_id: str) -> Dict[str, Any]:
        path = self._assistant_path(assistant_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local assistant: {assistant_id}")
        return json.loads(path.read_text())

    def _save_assistant(self, assistant: Dict[str, Any]) -> None:
        self._assistant_path(assistant["id"]).write_text(json.dumps(assistant, indent=2, sort_keys=True))

    def _load_thread(self, thread_id: str) -> Dict[str, Any]:
        path = self._thread_path(thread_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local thread: {thread_id}")
        return json.loads(path.read_text())

    def _save_thread(self, thread: Dict[str, Any]) -> None:
        self._thread_path(thread["id"]).write_text(json.dumps(thread, indent=2, sort_keys=True))

    def _load_conversation(self, conversation_id: str) -> Dict[str, Any]:
        path = self._conversation_path(conversation_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown local conversation: {conversation_id}")
        return json.loads(path.read_text())

    def _save_conversation(self, conversation: Dict[str, Any]) -> None:
        self._conversation_path(conversation["id"]).write_text(json.dumps(conversation, indent=2, sort_keys=True))

    def _thread_shape(self, thread: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": thread.get("id"),
            "object": "thread",
            "created_at": thread.get("created_at"),
            "metadata": thread.get("metadata", {}),
            "tool_resources": thread.get("tool_resources", {}),
            "oauth_compat_route": thread.get("oauth_compat_route"),
        }

    def _conversation_shape(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": conversation.get("id"),
            "object": "conversation",
            "created_at": conversation.get("created_at"),
            "metadata": conversation.get("metadata", {}),
            "item_count": len(conversation.get("items", [])),
            "oauth_compat_route": conversation.get("route"),
        }

    def _conversation_item_list_shape(
        self,
        items: list[Dict[str, Any]],
        *,
        has_more: bool = False,
    ) -> Dict[str, Any]:
        return {
            "object": "list",
            "route": "local_conversation_store",
            "data": items,
            "first_id": items[0].get("id") if items else None,
            "last_id": items[-1].get("id") if items else None,
            "has_more": has_more,
        }

    def _conversation_item_shape(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item_type = str(item.get("type") or "message")
        role = str(item.get("role") or "user")
        return {
            "type": item_type,
            "id": str(item.get("id") or f"msg-local-{uuid.uuid4().hex}"),
            "object": "conversation.item",
            "status": str(item.get("status") or "completed"),
            "role": role,
            "content": self._conversation_item_content(item.get("content")),
            "metadata": item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
            "created_at": int(time.time()),
            "oauth_compat_route": "local_conversation_store",
        }

    def _conversation_item_content(self, content: Any) -> list[Dict[str, Any]]:
        if isinstance(content, list):
            parts = [part for part in content if isinstance(part, dict)]
            if parts:
                return parts
        if isinstance(content, str):
            return [{"type": "input_text", "text": content}]
        if content is None:
            return []
        return [{"type": "input_text", "text": self.input_to_plain_text(content)}]

    def _chatkit_thread_shape(self, thread: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": thread.get("id"),
            "object": "chatkit.thread",
            "created_at": thread.get("created_at"),
            "metadata": thread.get("metadata", {}),
            "item_count": len(thread.get("items", [])),
            "route": thread.get("route"),
        }

    def _chatkit_item_shape(
        self,
        *,
        thread_id: str,
        role: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "id": f"ckitem-local-{uuid.uuid4().hex}",
            "object": "chatkit.thread.item",
            "thread_id": thread_id,
            "created_at": int(time.time()),
            "role": role,
            "content": self.input_to_plain_text(content),
            "metadata": metadata or {},
        }

    def _thread_message_shape(
        self,
        *,
        thread_id: str,
        role: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
        attachments: Optional[list[Dict[str, Any]]] = None,
        assistant_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        text = self.input_to_plain_text(content)
        return {
            "id": f"msg_local_{uuid.uuid4().hex}",
            "object": "thread.message",
            "created_at": int(time.time()),
            "thread_id": thread_id,
            "role": role if role in {"user", "assistant"} else "user",
            "content": [{
                "type": "text",
                "text": {"value": text, "annotations": []},
            }],
            "assistant_id": assistant_id,
            "run_id": run_id,
            "status": "completed",
            "completed_at": int(time.time()),
            "incomplete_at": None,
            "incomplete_details": None,
            "metadata": metadata or {},
            "attachments": attachments or [],
        }

    def _find_thread_message(self, thread_id: str, message_id: str) -> Dict[str, Any]:
        thread = self._load_thread(thread_id)
        for message in thread.get("messages", []):
            if message.get("id") == message_id:
                return message
        raise FileNotFoundError(f"Unknown local thread message: {message_id}")

    def _find_thread_run(self, thread_id: str, run_id: str) -> Dict[str, Any]:
        thread = self._load_thread(thread_id)
        for run in thread.get("runs", []):
            if run.get("id") == run_id:
                return run
        raise FileNotFoundError(f"Unknown local thread run: {run_id}")

    def _thread_transcript(self, thread: Dict[str, Any]) -> str:
        lines = []
        for message in thread.get("messages", []):
            role = message.get("role") or "user"
            text_parts = []
            for content in message.get("content", []):
                if isinstance(content, dict):
                    text = content.get("text")
                    if isinstance(text, dict) and isinstance(text.get("value"), str):
                        text_parts.append(text["value"])
            if text_parts:
                lines.append(f"{role}: {' '.join(text_parts)}")
        return "\n".join(lines)

    def _upload_summary(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": record.get("id"),
            "object": "oauth_compat.upload",
            "route": record.get("route"),
            "bytes": record.get("bytes"),
            "created_at": record.get("created_at"),
            "expires_at": record.get("expires_at"),
            "filename": record.get("filename"),
            "mime_type": record.get("mime_type"),
            "purpose": record.get("purpose"),
            "status": record.get("status"),
            "file": record.get("file"),
            "part_count": len(record.get("parts", [])),
        }

    def _upload_part_summary(self, part: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": part.get("id"),
            "object": "oauth_compat.upload.part",
            "route": part.get("route"),
            "created_at": part.get("created_at"),
            "upload_id": part.get("upload_id"),
            "bytes": part.get("bytes"),
        }

    def _batch_summary(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": record.get("id"),
            "object": "batch",
            "route": record.get("route"),
            "endpoint": record.get("endpoint"),
            "input_file_id": record.get("input_file_id"),
            "completion_window": record.get("completion_window"),
            "status": record.get("status"),
            "created_at": record.get("created_at"),
            "in_progress_at": record.get("in_progress_at"),
            "finalizing_at": record.get("finalizing_at"),
            "completed_at": record.get("completed_at"),
            "expires_at": record.get("expires_at"),
            "cancelling_at": record.get("cancelling_at"),
            "cancelled_at": record.get("cancelled_at"),
            "failed_at": record.get("failed_at"),
            "expired_at": record.get("expired_at"),
            "output_file_id": record.get("output_file_id"),
            "error_file_id": record.get("error_file_id"),
            "errors": record.get("errors"),
            "metadata": record.get("metadata", {}),
            "request_counts": record.get("request_counts", {"total": 0, "completed": 0, "failed": 0}),
        }

    def _local_batch_request_body(self, *, method: str, url: str, endpoint: str, body: Dict[str, Any]) -> Dict[str, Any]:
        if method != "POST":
            raise ValueError(f"Unsupported local batch method: {method}")
        route = url
        if route.startswith("https://api.openai.com"):
            route = route.removeprefix("https://api.openai.com")
        if route.startswith("/v1/"):
            route = route[3:]
        if endpoint.startswith("/v1/") and not url:
            route = endpoint[3:]
        if route == "/responses":
            result = self.responses_create(
                self.input_to_plain_text(body.get("input", "")),
                instructions=body.get("instructions") if isinstance(body.get("instructions"), str) else "Answer directly.",
            )
            text = str(result.get("output_text") or "")
            return {
                "id": f"resp_oauth_{uuid.uuid4().hex}",
                "object": "response",
                "created_at": int(time.time()),
                "model": result.get("model"),
                "output_text": text,
                "output": [{
                    "id": f"msg_{uuid.uuid4().hex}",
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": text}],
                }],
                "oauth_compat_route": result.get("route"),
            }
        if route == "/completions":
            result = self.completions_create(self.input_to_plain_text(body.get("prompt", "")))
            return {
                "id": f"cmpl_oauth_{uuid.uuid4().hex}",
                "object": "text_completion",
                "created": int(time.time()),
                "model": result.get("model"),
                "choices": [{
                    "text": result.get("text", ""),
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop",
                }],
                "oauth_compat_route": result.get("route"),
            }
        if route == "/chat/completions":
            messages = body.get("messages")
            if not isinstance(messages, list):
                raise ValueError("messages must be a list")
            result = self.chat_completions_create(messages)
            return {
                "id": f"chatcmpl_oauth_{uuid.uuid4().hex}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": result.get("model"),
                "choices": [{
                    "index": 0,
                    "message": result.get("message", {"role": "assistant", "content": ""}),
                    "finish_reason": "stop",
                }],
                "oauth_compat_route": result.get("route"),
            }
        if route == "/embeddings":
            return self.embeddings_create(self.input_to_plain_text(body.get("input", "")))
        if route == "/moderations":
            return self.moderations_create(body.get("input", ""), model=str(body.get("model") or "local-heuristic-moderation"))
        if route == "/images/generations":
            prompt = body.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("prompt must be a non-empty string")
            output_path = ARTIFACTS / f"compat_batch_image_{uuid.uuid4().hex}.png"
            result = self.images_generate(prompt, output_path, size=str(body.get("size") or "1024x1024"))
            image_bytes = Path(result["path"]).read_bytes()
            return {
                "created": int(time.time()),
                "data": [{"b64_json": base64.b64encode(image_bytes).decode("ascii")}],
                "oauth_compat_route": result.get("route"),
                "local_path": result.get("path"),
            }
        raise ValueError(f"Unsupported local batch route: {route}")

    def input_to_plain_text(self, input_value: Any) -> str:
        if isinstance(input_value, str):
            return input_value
        if isinstance(input_value, list):
            parts: list[str] = []
            for item in input_value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("input_text") or item.get("content")
                    if isinstance(text, str):
                        parts.append(text)
                    elif isinstance(text, list):
                        parts.append(self.input_to_plain_text(text))
            return "\n".join(part for part in parts if part)
        if isinstance(input_value, dict):
            return self.input_to_plain_text([input_value])
        return str(input_value)

    def _moderation_result(self, text: str) -> Dict[str, Any]:
        lowered = text.lower()
        rules = {
            "harassment": ("idiot", "stupid", "moron"),
            "harassment/threatening": ("i will hurt", "threaten"),
            "hate": ("racial slur", "hate group"),
            "hate/threatening": ("kill all", "exterminate"),
            "illicit": ("sell stolen", "make fake id", "bypass security"),
            "illicit/violent": ("build a bomb", "make a weapon"),
            "self-harm": ("self harm", "suicide", "kill myself"),
            "self-harm/intent": ("i want to die", "end my life"),
            "self-harm/instructions": ("how to cut", "how to hang"),
            "sexual": ("explicit sex", "porn"),
            "sexual/minors": ("sexual minor", "underage sex"),
            "violence": ("kill", "stab", "shoot"),
            "violence/graphic": ("gore", "dismember"),
        }
        categories = {name: any(term in lowered for term in terms) for name, terms in rules.items()}
        category_scores = {name: 0.92 if value else 0.01 for name, value in categories.items()}
        applied = {
            "harassment": ["text"],
            "harassment/threatening": ["text"],
            "hate": ["text"],
            "hate/threatening": ["text"],
            "illicit": ["text"],
            "illicit/violent": ["text"],
            "self-harm": ["text"],
            "self-harm/intent": ["text"],
            "self-harm/instructions": ["text"],
            "sexual": ["text"],
            "sexual/minors": ["text"],
            "violence": ["text"],
            "violence/graphic": ["text"],
        }
        return {
            "flagged": any(categories.values()),
            "categories": categories,
            "category_scores": category_scores,
            "category_applied_input_types": applied,
            "oauth_compat_route": "local_heuristic_moderation",
        }

    def _vector_store_summary(self, store: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": store["id"],
            "object": "oauth_compat.vector_store",
            "route": store.get("route"),
            "name": store.get("name"),
            "created_at": store.get("created_at"),
            "item_count": len(store.get("items", [])),
        }

    def _vector_store_file_summary(self, store: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("file_id"),
            "object": "oauth_compat.vector_store.file",
            "route": store.get("route"),
            "vector_store_id": store.get("id"),
            "status": "completed",
            "created_at": item.get("created_at"),
            "usage_bytes": len(str(item.get("text", "")).encode("utf-8")),
            "attributes": item.get("metadata", {}).get("attributes", {}),
            "metadata": {
                "local_item_id": item.get("id"),
                "filename": item.get("metadata", {}).get("filename"),
            },
        }

    def _eval_summary(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": record.get("id"),
            "object": "eval",
            "created_at": record.get("created_at"),
            "name": record.get("name"),
            "data_source_config": record.get("data_source_config", {}),
            "testing_criteria": record.get("testing_criteria", []),
            "metadata": record.get("metadata", {}),
            "route": record.get("route"),
        }

    def _eval_run_summary(self, run: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": run.get("id"),
            "object": "eval.run",
            "created_at": run.get("created_at"),
            "eval_id": run.get("eval_id"),
            "name": run.get("name"),
            "metadata": run.get("metadata", {}),
            "data_source": run.get("data_source", {}),
            "status": run.get("status", "completed"),
            "model": run.get("model"),
            "error": run.get("error"),
            "report_url": run.get("report_url"),
            "per_model_usage": run.get("per_model_usage", []),
            "per_testing_criteria_results": run.get("per_testing_criteria_results", []),
            "result_counts": run.get("result_counts", {}),
            "route": run.get("route"),
        }

    def _find_eval_run(self, eval_id: str, run_id: str) -> Dict[str, Any]:
        record = self._load_eval(eval_id)
        for run in record.get("runs", []):
            if run.get("id") == run_id:
                return run
        raise FileNotFoundError(f"Unknown local eval run: {run_id}")

    def _eval_output_item_shape(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id"),
            "object": "eval.run.output_item",
            "created_at": item.get("created_at"),
            "eval_id": item.get("eval_id"),
            "run_id": item.get("run_id"),
            "status": item.get("status"),
            "datasource_item_id": item.get("datasource_item_id"),
            "datasource_item": item.get("datasource_item", {}),
            "sample": item.get("sample", {}),
            "results": item.get("results", []),
        }

    def _validate_local_grader(self, grader: Dict[str, Any]) -> tuple[bool, list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        grader_type = grader.get("type")
        if grader_type == "string_check":
            for key in ("name", "input", "reference", "operation"):
                if not isinstance(grader.get(key), str) or not str(grader.get(key)).strip():
                    errors.append(f"{key} must be a non-empty string")
            operation = str(grader.get("operation") or "")
            if operation not in {"eq", "ne", "neq", "like", "ilike"}:
                errors.append("operation must be one of eq, ne, neq, like, ilike")
        elif grader_type == "multi":
            graders = grader.get("graders")
            if not isinstance(graders, dict) or not graders:
                errors.append("graders must be a non-empty object")
            else:
                for name, child in graders.items():
                    if not isinstance(child, dict):
                        errors.append(f"graders.{name} must be an object")
                        continue
                    child_valid, child_errors, child_warnings = self._validate_local_grader(child)
                    if not child_valid:
                        errors.extend(f"graders.{name}: {error}" for error in child_errors)
                    warnings.extend(f"graders.{name}: {warning}" for warning in child_warnings)
            calculate_output = grader.get("calculate_output")
            if calculate_output is not None:
                if not isinstance(calculate_output, str) or not calculate_output.strip():
                    errors.append("calculate_output must be a non-empty string when provided")
                elif isinstance(graders, dict):
                    try:
                        self._safe_grader_expression(calculate_output, {str(name): 0.0 for name in graders})
                    except ValueError as exc:
                        errors.append(f"calculate_output is not supported locally: {exc}")
        else:
            errors.append(f"unsupported local grader type: {grader_type or '<missing>'}")
            warnings.append("Local grader run supports string_check and multi only; hosted/model/python graders still need Platform API support.")
        return not errors, errors, warnings

    def _run_local_grader(
        self,
        grader: Dict[str, Any],
        *,
        sample: Dict[str, Any],
        item: Dict[str, Any],
    ) -> Dict[str, Any]:
        valid, errors, warnings = self._validate_local_grader(grader)
        grader_type = str(grader.get("type") or "")
        name = str(grader.get("name") or grader_type or "grader")
        if not valid:
            unsupported = any(error.startswith("unsupported local grader type") for error in errors)
            return self._grader_error_result(
                name=name,
                grader_type=grader_type,
                errors=errors,
                warnings=warnings,
                unsupported=unsupported,
            )
        if grader_type == "string_check":
            return self._run_string_check_grader(grader, sample=sample, item=item)
        if grader_type == "multi":
            return self._run_multi_grader(grader, sample=sample, item=item)
        return self._grader_error_result(
            name=name,
            grader_type=grader_type,
            errors=[f"unsupported local grader type: {grader_type}"],
            warnings=warnings,
            unsupported=True,
        )

    def _run_string_check_grader(
        self,
        grader: Dict[str, Any],
        *,
        sample: Dict[str, Any],
        item: Dict[str, Any],
    ) -> Dict[str, Any]:
        input_text = self._render_grader_template(str(grader.get("input") or ""), sample=sample, item=item)
        reference_text = self._render_grader_template(str(grader.get("reference") or ""), sample=sample, item=item)
        operation = str(grader.get("operation") or "")
        if operation == "eq":
            passed = input_text == reference_text
        elif operation in {"ne", "neq"}:
            passed = input_text != reference_text
        elif operation == "like":
            passed = reference_text in input_text
        elif operation == "ilike":
            passed = reference_text.lower() in input_text.lower()
        else:
            return self._grader_error_result(
                name=str(grader.get("name") or "string_check"),
                grader_type="string_check",
                errors=[f"unsupported operation: {operation}"],
                warnings=[],
                unsupported=False,
            )
        reward = 1.0 if passed else 0.0
        name = str(grader.get("name") or "string_check")
        return {
            "reward": reward,
            "sub_rewards": {},
            "metadata": {
                "name": name,
                "type": "string_check",
                "operation": operation,
                "input": self._truncate_grader_value(input_text),
                "reference": self._truncate_grader_value(reference_text),
                "passed": passed,
                "errors": {
                    "invalid_grader": False,
                    "unsupported_grader_type": False,
                    "other_error": None,
                },
                "scores": {name: reward},
            },
        }

    def _run_multi_grader(
        self,
        grader: Dict[str, Any],
        *,
        sample: Dict[str, Any],
        item: Dict[str, Any],
    ) -> Dict[str, Any]:
        graders = grader.get("graders") if isinstance(grader.get("graders"), dict) else {}
        sub_rewards: Dict[str, float] = {}
        sub_metadata: Dict[str, Any] = {}
        for name, child in graders.items():
            child_result = self._run_local_grader(child, sample=sample, item=item)
            reward = float(child_result.get("reward", 0.0))
            sub_rewards[str(name)] = reward
            sub_metadata[str(name)] = child_result.get("metadata", {})
        calculate_output = grader.get("calculate_output")
        try:
            if isinstance(calculate_output, str) and calculate_output.strip():
                reward = self._safe_grader_expression(calculate_output, sub_rewards)
            elif sub_rewards:
                reward = sum(sub_rewards.values()) / len(sub_rewards)
            else:
                reward = 0.0
        except ValueError as exc:
            return self._grader_error_result(
                name=str(grader.get("name") or "multi"),
                grader_type="multi",
                errors=[f"calculate_output failed: {exc}"],
                warnings=[],
                unsupported=False,
            )
        reward = max(0.0, min(1.0, float(reward)))
        name = str(grader.get("name") or "multi")
        return {
            "reward": reward,
            "sub_rewards": sub_rewards,
            "metadata": {
                "name": name,
                "type": "multi",
                "calculate_output": calculate_output,
                "errors": {
                    "invalid_grader": False,
                    "unsupported_grader_type": False,
                    "other_error": None,
                },
                "scores": {name: reward, **sub_rewards},
                "sub_metadata": sub_metadata,
            },
        }

    def _grader_error_result(
        self,
        *,
        name: str,
        grader_type: str,
        errors: list[str],
        warnings: list[str],
        unsupported: bool,
    ) -> Dict[str, Any]:
        return {
            "reward": 0.0,
            "sub_rewards": {},
            "metadata": {
                "name": name,
                "type": grader_type,
                "errors": {
                    "invalid_grader": not unsupported,
                    "unsupported_grader_type": unsupported,
                    "other_error": "; ".join(errors) if errors else None,
                },
                "warnings": warnings,
                "scores": {name: 0.0},
            },
        }

    def _normalize_grader_sample(self, model_sample: Any) -> Dict[str, Any]:
        if isinstance(model_sample, str):
            return {"output_text": model_sample}
        if not isinstance(model_sample, dict):
            raise ValueError("model_sample must be a string or object")
        sample = dict(model_sample)
        if not isinstance(sample.get("output_text"), str):
            output_text = self._extract_sample_output_text(sample)
            if output_text is not None:
                sample["output_text"] = output_text
        sample.setdefault("output_text", "")
        return sample

    def _extract_sample_output_text(self, sample: Dict[str, Any]) -> Optional[str]:
        for key in ("content", "output", "text"):
            value = sample.get(key)
            if isinstance(value, str):
                return value
        message = sample.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
        choices = sample.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                if isinstance(first.get("text"), str):
                    return first["text"]
                message = first.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message["content"]
        return None

    def _render_grader_template(self, template: str, *, sample: Dict[str, Any], item: Dict[str, Any]) -> str:
        def replace(match: re.Match[str]) -> str:
            value = self._resolve_grader_template_path(match.group(1).strip(), sample=sample, item=item)
            if value is None:
                return ""
            if isinstance(value, (dict, list)):
                return json.dumps(value, sort_keys=True)
            return str(value)

        return re.sub(r"\{\{\s*([^{}]+?)\s*\}\}", replace, template)

    def _resolve_grader_template_path(self, expression: str, *, sample: Dict[str, Any], item: Dict[str, Any]) -> Any:
        if expression == "model_sample":
            return sample.get("output_text", "")
        if "." not in expression:
            if expression in {"output", "output_text"}:
                return sample.get("output_text", "")
            return ""
        namespace, remainder = expression.split(".", 1)
        if namespace == "sample":
            current: Any = sample
        elif namespace == "item":
            current = item
        else:
            return ""
        for segment in remainder.split("."):
            current = self._resolve_grader_template_segment(current, segment)
            if current is None:
                return ""
        return current

    def _resolve_grader_template_segment(self, current: Any, segment: str) -> Any:
        matched = False
        for match in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]", segment):
            matched = True
            key = match.group(1)
            index = match.group(2)
            if key is not None:
                if not isinstance(current, dict):
                    return None
                current = current.get(key)
            elif index is not None:
                if not isinstance(current, list):
                    return None
                position = int(index)
                if position >= len(current):
                    return None
                current = current[position]
        return current if matched else None

    def _safe_grader_expression(self, expression: str, values: Dict[str, float]) -> float:
        allowed_nodes = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Mod,
            ast.Pow,
            ast.USub,
            ast.UAdd,
            ast.Constant,
            ast.Name,
            ast.Load,
        )
        tree = ast.parse(expression, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise ValueError(f"unsupported expression node {type(node).__name__}")
            if isinstance(node, ast.Name) and node.id not in values:
                raise ValueError(f"unknown grader score {node.id}")
            if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
                raise ValueError("only numeric constants are supported")
        return float(eval(compile(tree, "<grader_expression>", "eval"), {"__builtins__": {}}, values))

    def _truncate_grader_value(self, value: str, limit: int = 500) -> str:
        if len(value) <= limit:
            return value
        return value[:limit] + "...[truncated]"

    def _extract_eval_case(
        self,
        data_source: Dict[str, Any],
        run_metadata: Dict[str, Any],
        eval_metadata: Dict[str, Any],
    ) -> tuple[str, str]:
        candidates = [run_metadata, eval_metadata]
        for item in self._iter_eval_data_source_items(data_source):
            candidates.append(item)
        prompt = None
        expected = None
        for item in candidates:
            if not isinstance(item, dict):
                continue
            prompt = prompt or item.get("prompt") or item.get("input")
            expected = expected or item.get("expected_substring") or item.get("expected") or item.get("reference")
        if not isinstance(prompt, str) or not prompt.strip():
            prompt = "Reply exactly: local eval ok"
        if not isinstance(expected, str) or not expected:
            expected = "local eval ok"
        return prompt, expected

    def _iter_eval_data_source_items(self, data_source: Dict[str, Any]) -> list[Dict[str, Any]]:
        source = data_source.get("source") if isinstance(data_source, dict) else None
        if not isinstance(source, dict):
            return []
        content = source.get("content")
        if not isinstance(content, list):
            return []
        items = []
        for entry in content:
            if not isinstance(entry, dict):
                continue
            item = entry.get("item")
            if isinstance(item, dict):
                items.append(item)
        return items

    def _find_vector_store_file_batch(self, store_id: str, batch_id: str) -> Dict[str, Any]:
        store = self._load_vector_store(store_id)
        for batch in store.get("file_batches", []):
            if batch.get("id") == batch_id:
                return batch
        raise FileNotFoundError(f"Unknown local vector store file batch: {batch_id}")

    def _vector_store_file_batch_summary(self, batch: Dict[str, Any]) -> Dict[str, Any]:
        file_ids = [file_id for file_id in batch.get("file_ids", []) if isinstance(file_id, str)]
        status = str(batch.get("status") or "completed")
        completed = len(file_ids) if status == "completed" else 0
        cancelled = len(file_ids) if status == "cancelled" else 0
        return {
            "id": batch.get("id"),
            "object": "oauth_compat.vector_store.file_batch",
            "route": batch.get("route"),
            "vector_store_id": batch.get("vector_store_id"),
            "created_at": batch.get("created_at"),
            "status": status,
            "file_counts": {
                "in_progress": 0,
                "completed": completed,
                "failed": 0,
                "cancelled": cancelled,
                "total": len(file_ids),
            },
        }

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
            "local_upload_session_plus_chatgpt_backend_files",
            "local_batch_processor",
            "local_heuristic_moderation",
            "local_response_store_plus_codex_text",
            "local_chat_completion_store_plus_codex_text",
            "local_file_metadata",
            "local_vector_store_plus_oauth_embeddings",
            "local_eval_plus_codex_text",
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
