from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from generate_client_config import build_report as build_client_config_report
from generate_coverage_map import build_report as build_coverage_map_report
from status_report import build_report as build_status_report
from classify_openai_path import classify as classify_openai_path
from oauth_feature_router import ROOT, OAuthFeatureRouter
from platform_fallback import ACCESS_TOKEN_ENV, API_KEY_ENV, ADMIN_KEY_ENV, ENABLE_ENV, MODE_ENV, path_fallback_state


REPORTS = ROOT / "reports"


class RouterOfflineSmoke:
    def __init__(self) -> None:
        self.rows: list[Dict[str, Any]] = []
        self.router = OAuthFeatureRouter()
        self.router.oauth.codex_text = self.fake_codex_text
        self.router.oauth.official_embedding = self.fake_embedding
        self.router.oauth.official_transcribe_audio = self.fake_transcription
        self.router.oauth.codex_vision = self.fake_vision
        self.router.oauth.codex_generate_image = self.fake_generate_image
        self.router.oauth.realtime_client_secret_payload = self.fake_realtime_client_secret_payload
        self.router.oauth.realtime_transcription_session = self.fake_realtime_transcription_session

    def fake_codex_text(self, prompt: str, *, instructions: str = "Answer directly.") -> str:
        return "offline router text ok"

    def fake_embedding(self, text: str, *, model: str = "text-embedding-3-small") -> Dict[str, Any]:
        return {"object": "list", "data": [{"embedding": [0.1] * 1536}]}

    def fake_transcription(self, audio_path: Path | str, *, model: str = "gpt-4o-mini-transcribe") -> Dict[str, Any]:
        return {"object": "audio.transcription", "text": "hola mundo", "_http_status": 200}

    def fake_realtime_client_secret_payload(
        self,
        *,
        session: Optional[Dict[str, Any]] = None,
        expires_after: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "object": "realtime.client_secret",
            "value": "offline-realtime-secret",
            "expires_at": int(time.time()) + 600,
            "_http_status": 200,
        }

    def fake_realtime_transcription_session(
        self,
        *,
        session: Optional[Dict[str, Any]] = None,
        expires_after: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.fake_realtime_client_secret_payload(session=session, expires_after=expires_after)

    def fake_vision(self, image_path: Path | str, prompt: str) -> str:
        return "offline source image"

    def fake_generate_image(self, prompt: str, output_path: Path | str, *, size: str = "1024x1024") -> Path:
        path = Path(output_path)
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"offline image bytes")
        return path

    def record(self, name: str, fn: Callable[[], Dict[str, Any]], expect: Callable[[Dict[str, Any]], bool]) -> None:
        try:
            payload = fn()
            row: Dict[str, Any] = {"name": name, **self.summarize(payload)}
            row["status"] = "pass" if expect(payload) else "fail"
        except Exception as exc:
            row = {
                "name": name,
                "status": "fail",
                "error_type": type(exc).__name__,
                "error": str(exc)[:600],
            }
        self.rows.append(row)
        print(f"[{row['status']}] {name}")

    def summarize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        row: Dict[str, Any] = {}
        for key in ("id", "object", "route", "oauth_compat_route", "status"):
            value = payload.get(key)
            if isinstance(value, str):
                row[key] = value[:80]
        data = payload.get("data")
        if isinstance(data, list):
            row["data_count"] = len(data)
            if data and isinstance(data[0], dict) and isinstance(data[0].get("id"), str):
                row["first_id"] = data[0]["id"]
        if isinstance(payload.get("output_text"), str):
            row["output_text_len"] = len(payload["output_text"])
        if isinstance(payload.get("message"), dict):
            message = payload["message"]
            if isinstance(message.get("content"), str):
                row["message_len"] = len(message["content"])
        if isinstance(payload.get("passed"), bool):
            row["passed"] = payload["passed"]
        if isinstance(payload.get("deleted"), bool):
            row["deleted"] = payload["deleted"]
        if isinstance(payload.get("http_status"), int):
            row["http_status"] = payload["http_status"]
        if isinstance(payload.get("matched_path"), str):
            row["matched_path"] = payload["matched_path"]
        if isinstance(payload.get("category"), str):
            row["category"] = payload["category"]
        fallback = payload.get("fallback")
        if isinstance(fallback, dict):
            row["fallback_can_forward"] = fallback.get("can_forward")
            row["fallback_credential_env"] = fallback.get("credential_env")
            row["fallback_credential_present"] = fallback.get("credential_present")
        return row

    def fallback_state_with_env(self, path: str, category: str, env: Dict[str, str | None]) -> Dict[str, Any]:
        keys = {ENABLE_ENV, API_KEY_ENV, ADMIN_KEY_ENV, ACCESS_TOKEN_ENV, *env.keys()}
        old = {key: os.environ.get(key) for key in keys}
        try:
            for key in keys:
                os.environ.pop(key, None)
            for key, value in env.items():
                if value is not None:
                    os.environ[key] = value
            return {
                "path": path,
                "category": category,
                "fallback": path_fallback_state(path, category=category),
            }
        finally:
            for key in keys:
                os.environ.pop(key, None)
                if old.get(key) is not None:
                    os.environ[key] = str(old[key])

    def fine_tuning_jobs_payload(self) -> Dict[str, Any]:
        job = self.router.fine_tuning_jobs_create(
            model="gpt-5.5",
            training_file="file-local-training",
            validation_file="file-local-validation",
            metadata={"source": "offline-smoke"},
        )
        job_id = job["id"]
        paused = self.router.fine_tuning_jobs_pause(job_id)
        checkpoints = self.router.fine_tuning_job_checkpoints_list(job_id)
        checkpoint_id = checkpoints["data"][0]["id"]
        permission = self.router.fine_tuning_checkpoint_permissions_create(
            checkpoint_id,
            project_id="proj-local-smoke",
        )
        permissions = self.router.fine_tuning_checkpoint_permissions_list(checkpoint_id)
        deleted = self.router.fine_tuning_checkpoint_permissions_delete(checkpoint_id, permission["id"])
        return {
            "object": "oauth_compat.fine_tuning.jobs.smoke",
            "route": "local_fine_tuning_job_store",
            "job": job,
            "list": self.router.fine_tuning_jobs_list(),
            "retrieve": self.router.fine_tuning_jobs_retrieve(job_id),
            "paused": paused,
            "resumed": self.router.fine_tuning_jobs_resume(job_id),
            "cancelled": self.router.fine_tuning_jobs_cancel(job_id),
            "events": self.router.fine_tuning_job_events_list(job_id),
            "checkpoints": checkpoints,
            "permission": permission,
            "permissions": permissions,
            "deleted": deleted,
        }

    def organization_project_sandbox_payload(self) -> Dict[str, Any]:
        project_id = "proj-local-default"
        return {
            "object": "oauth_compat.organization_project_sandbox.smoke",
            "route": "local_organization_project_sandbox",
            "projects": self.router.organization_sandbox("/v1/organization/projects"),
            "project": self.router.organization_sandbox(f"/v1/organization/projects/{project_id}"),
            "archive": self.router.organization_sandbox(
                f"/v1/organization/projects/{project_id}/archive",
                method="POST",
            ),
            "project_roles": self.router.organization_sandbox(f"/v1/projects/{project_id}/roles"),
            "user_role_delete": self.router.organization_sandbox(
                "/v1/organization/users/user-local-owner/roles/role-local-admin",
                method="DELETE",
            ),
            "usage": self.router.organization_sandbox("/v1/organization/usage/completions"),
            "costs": self.router.organization_sandbox("/v1/organization/costs"),
        }

    def videos_storyboard_payload(self) -> Dict[str, Any]:
        video = self.router.videos_create(
            prompt="Offline storyboard video",
            model="sora-local-storyboard",
            size="1280x720",
            seconds="4",
            metadata={"source": "offline-smoke"},
        )
        video_id = video["id"]
        content, content_type = self.router.videos_content(video_id)
        remix = self.router.videos_remix(video_id, prompt="Offline remix storyboard")
        edit = self.router.videos_create(prompt="Offline edit storyboard", operation="edit")
        extension = self.router.videos_create(prompt="Offline extension storyboard", operation="extension")
        characters = self.router.video_characters_list()
        return {
            "object": "oauth_compat.videos.storyboard.smoke",
            "route": "local_video_storyboard_sandbox",
            "video": video,
            "list": self.router.videos_list(),
            "retrieve": self.router.videos_retrieve(video_id),
            "content_type": content_type,
            "content_len": len(content),
            "remix": remix,
            "edit": edit,
            "extension": extension,
            "characters": characters,
            "character": self.router.video_characters_retrieve("vchar-local-default"),
            "deleted": self.router.videos_delete(video_id),
        }

    def run(self, *, write: bool = True) -> int:
        self.record(
            "responses_create",
            lambda: self.router.responses_create("Reply exactly: offline ok"),
            lambda payload: payload.get("output_text") == "offline router text ok",
        )
        self.record(
            "responses_input_tokens_estimate",
            lambda: self.router.responses_input_tokens_estimate("Count this local prompt"),
            lambda payload: payload.get("estimated") is True
            and isinstance(payload.get("input_tokens"), int)
            and payload["input_tokens"] > 0,
        )
        self.record(
            "responses_compact",
            lambda: self.router.responses_compact("Compact this offline prompt and preserve compact-ok."),
            lambda payload: payload.get("object") == "oauth_compat.response.compaction"
            and payload.get("route") == "local_responses_compact_plus_codex_text"
            and isinstance(payload.get("encrypted_content"), str)
            and bool(payload["encrypted_content"]),
        )
        self.record(
            "audio_translations_create",
            lambda: self.router.audio_translations_create(ROOT / "missing-audio-is-faked.wav"),
            lambda payload: payload.get("object") == "audio.translation"
            and payload.get("route") == "official_audio_transcriptions_plus_codex_translation"
            and payload.get("text") == "offline router text ok",
        )
        self.record(
            "audio_voice_catalog",
            lambda: (
                lambda consent: {
                    "created_consent": consent,
                    "updated_consent": self.router.audio_voice_consents_update(consent["id"], name="Updated offline consent"),
                    "retrieved_consent": self.router.audio_voice_consents_retrieve(consent["id"]),
                    "created_voice": self.router.audio_voices_create(
                        name="Offline local voice",
                        consent=consent["id"],
                        audio_sample_path=ROOT / "README.md",
                        mime_type="text/markdown",
                    ),
                    "voices": self.router.audio_voices_list(),
                    "consents": self.router.audio_voice_consents_list(),
                    "deleted_consent": self.router.audio_voice_consents_delete(consent["id"]),
                }
            )(self.router.audio_voice_consents_create(
                name="Offline consent",
                language="en-US",
                recording_path=ROOT / "README.md",
                mime_type="text/markdown",
            )),
            lambda payload: payload["created_consent"].get("object") == "audio.voice_consent"
            and payload["updated_consent"].get("name") == "Updated offline consent"
            and payload["retrieved_consent"].get("id") == payload["created_consent"].get("id")
            and payload["created_voice"].get("object") == "audio.voice"
            and payload["created_voice"].get("hosted_voice_created") is False
            and any(item.get("id") == "alloy" for item in payload["voices"].get("data") or [])
            and any(item.get("id") == payload["created_consent"].get("id") for item in payload["consents"].get("data") or [])
            and payload["deleted_consent"].get("deleted") is True,
        )
        self.record(
            "realtime_sessions_aliases",
            lambda: {
                "session": self.router.realtime_sessions_create({"model": "gpt-realtime"}),
                "transcription": self.router.realtime_transcription_sessions_create({}),
            },
            lambda payload: payload["session"].get("object") == "realtime.session"
            and payload["session"].get("oauth_compat_route") == "official_realtime_client_secrets_session_alias"
            and payload["session"].get("client_secret", {}).get("value") == "offline-realtime-secret"
            and payload["transcription"].get("object") == "realtime.transcription_session"
            and payload["transcription"].get("session", {}).get("type") == "transcription"
            and payload["transcription"].get("client_secret", {}).get("value") == "offline-realtime-secret",
        )
        self.record(
            "realtime_call_lifecycle",
            lambda call_id=f"call_offline_{int(time.time() * 1000)}": {
                "accept": self.router.realtime_call_lifecycle(call_id, "accept", {"note": "start"}),
                "refer": self.router.realtime_call_lifecycle(call_id, "refer", {"target": "sip:agent@example.com"}),
                "hangup": self.router.realtime_call_lifecycle(call_id, "hangup", {}),
                "reject": self.router.realtime_call_lifecycle(f"{call_id}_reject", "reject", {"reason": "busy"}),
            },
            lambda payload: payload["accept"].get("status") == "in_progress"
            and payload["refer"].get("status") == "referred"
            and payload["hangup"].get("status") == "completed"
            and len(payload["hangup"].get("events") or []) == 3
            and payload["reject"].get("status") == "rejected"
            and payload["hangup"].get("oauth_compat_route") == "local_realtime_call_lifecycle_state",
        )
        self.record(
            "images_edit",
            lambda: self.router.images_edit(
                ROOT / "missing-image-is-faked.png",
                "make the background white",
                ROOT / "artifacts" / "offline_image_edit.png",
            ),
            lambda payload: payload.get("object") == "oauth_compat.image.edit"
            and payload.get("route") == "codex_vision_plus_image_generation_edit"
            and payload.get("source_description_chars") == len("offline source image"),
        )
        self.record(
            "images_variation",
            lambda: self.router.images_variation(
                ROOT / "missing-image-is-faked.png",
                ROOT / "artifacts" / "offline_image_variation.png",
            ),
            lambda payload: payload.get("object") == "oauth_compat.image.variation"
            and payload.get("route") == "codex_vision_plus_image_generation_variation"
            and payload.get("source_description_chars") == len("offline source image"),
        )
        container = self.router.containers_create(name="offline-container")
        container_file = self.router.container_files_create(
            container["id"],
            ROOT / "README.md",
            filename="README.md",
            mime_type="text/markdown",
        )
        self.record(
            "containers_files",
            lambda: {
                "container": self.router.containers_retrieve(container["id"]),
                "files": self.router.container_files_list(container["id"]),
                "file": self.router.container_files_retrieve(container["id"], container_file["id"]),
                "content": self.router.container_files_content(container["id"], container_file["id"])[0],
            },
            lambda payload: payload["container"].get("object") == "container"
            and len(payload["files"].get("data") or []) == 1
            and payload["file"].get("object") == "container.file"
            and len(payload["content"]) > 0,
        )
        chatkit_thread = self.router.chatkit_threads_create(items=[{"role": "user", "content": "hello chatkit"}])
        chatkit_session = self.router.chatkit_sessions_create(thread_id=chatkit_thread["id"], model="gpt-5.5")
        self.record(
            "chatkit_sessions_threads",
            lambda: {
                "thread": self.router.chatkit_threads_retrieve(chatkit_thread["id"]),
                "items": self.router.chatkit_thread_items_list(chatkit_thread["id"]),
                "cancelled": self.router.chatkit_sessions_cancel(chatkit_session["id"]),
            },
            lambda payload: payload["thread"].get("object") == "chatkit.thread"
            and len(payload["items"].get("data") or []) == 1
            and payload["cancelled"].get("status") == "cancelled",
        )
        skill = self.router.skills_create(
            name="offline-skill",
            description="Offline smoke skill",
            content="Use this skill only for offline smoke verification.",
        )
        skill_version = self.router.skill_versions_create(
            skill["id"],
            content="Second offline smoke skill version.",
        )
        self.record(
            "skills_registry",
            lambda: {
                "list": self.router.skills_list(limit=100),
                "skill": self.router.skills_retrieve(skill["id"]),
                "content": self.router.skill_content(skill["id"])[0],
                "versions": self.router.skill_versions_list(skill["id"]),
                "version": self.router.skill_version_retrieve(skill["id"], skill_version["version"]),
                "version_content": self.router.skill_version_content(skill["id"], skill_version["version"])[0],
                "updated": self.router.skills_update_default_version(skill["id"], default_version="1"),
                "deleted_version": self.router.skill_version_delete(skill["id"], skill_version["version"]),
                "deleted": self.router.skills_delete(skill["id"]),
            },
            lambda payload: any(item.get("id") == skill["id"] for item in payload["list"].get("data") or [])
            and payload["skill"].get("object") == "skill"
            and len(payload["content"]) > 0
            and len(payload["versions"].get("data") or []) == 2
            and payload["version"].get("object") == "skill.version"
            and len(payload["version_content"]) > 0
            and payload["updated"].get("default_version") == "1"
            and payload["deleted_version"].get("deleted") is True
            and payload["deleted"].get("deleted") is True,
        )
        conversation = self.router.conversations_create(
            items=[{"type": "message", "role": "user", "content": "hello conversation"}],
            metadata={"topic": "offline"},
        )
        added_items = self.router.conversation_items_create(
            conversation["id"],
            items=[{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "second"}]}],
        )
        added_id = added_items["data"][0]["id"]
        self.record(
            "conversations_items",
            lambda: {
                "conversation": self.router.conversations_retrieve(conversation["id"]),
                "updated": self.router.conversations_update(conversation["id"], metadata={"topic": "updated"}),
                "items": self.router.conversation_items_list(conversation["id"], order="asc"),
                "item": self.router.conversation_items_retrieve(conversation["id"], added_id),
                "after_delete_item": self.router.conversation_items_delete(conversation["id"], added_id),
                "deleted": self.router.conversations_delete(conversation["id"]),
            },
            lambda payload: payload["conversation"].get("object") == "conversation"
            and payload["updated"].get("metadata", {}).get("topic") == "updated"
            and len(payload["items"].get("data") or []) == 2
            and payload["item"].get("id") == added_id
            and payload["after_delete_item"].get("item_count") == 1
            and payload["deleted"].get("deleted") is True,
        )
        self.record(
            "completions_create",
            lambda: self.router.completions_create("Complete this offline prompt"),
            lambda payload: payload.get("text") == "offline router text ok"
            and payload.get("object") == "oauth_compat.completion",
        )
        self.record(
            "chat_create",
            lambda: self.router.chat_completions_create([{"role": "user", "content": "hello"}]),
            lambda payload: payload.get("object") == "oauth_compat.chat.completion"
            and isinstance(payload.get("message"), dict)
            and bool(payload["message"].get("content")),
        )
        assistant = self.router.assistants_create(
            model="gpt-5.5",
            name="offline-assistant",
            instructions="Reply briefly.",
        )
        thread = self.router.threads_create(messages=[{"role": "user", "content": "hello"}])
        message = self.router.thread_messages_create(thread["id"], role="user", content="second message")
        run = self.router.thread_runs_create(thread["id"], assistant_id=assistant["id"])
        self.record(
            "assistant_thread_run",
            lambda: run,
            lambda payload: payload.get("status") == "completed"
            and payload.get("object") == "thread.run",
        )
        self.record(
            "thread_run_steps",
            lambda: self.router.thread_run_steps_list(thread["id"], run["id"]),
            lambda payload: len(payload.get("data") or []) == 1,
        )
        self.record(
            "thread_message_delete",
            lambda: self.router.thread_messages_delete(thread["id"], message["id"]),
            lambda payload: payload.get("deleted") is True,
        )
        self.record(
            "moderations",
            lambda: self.router.moderations_create("hello from offline smoke"),
            lambda payload: len(payload.get("results") or []) == 1
            and payload["results"][0].get("flagged") is False,
        )
        self.record(
            "client_config_report",
            lambda: build_client_config_report(),
            lambda payload: isinstance(payload.get("base_url"), str)
            and payload["base_url"].endswith("/v1")
            and isinstance(payload.get("python_sdk"), dict)
            and isinstance(payload.get("javascript_sdk"), dict)
            and isinstance(payload.get("goal_complete"), bool),
        )
        self.record(
            "coverage_map_report",
            lambda: build_coverage_map_report(),
            lambda payload: isinstance(payload.get("groups"), list)
            and bool(payload["groups"])
            and isinstance(payload.get("goal_complete"), bool),
        )
        self.record(
            "status_report",
            lambda: build_status_report(
                host="127.0.0.1",
                port=8787,
                timeout_seconds=0.1,
                refresh_env=False,
                write_dependencies=False,
            ),
            lambda payload: isinstance(payload.get("base_url"), str)
            and payload["base_url"].endswith("/v1")
            and isinstance(payload.get("goal_complete"), bool)
            and isinstance(payload.get("next_actions"), list)
            and bool(payload["next_actions"]),
        )
        self.record(
            "template_local_classification",
            lambda: classify_openai_path("/v1/videos/video_123/remix"),
            lambda payload: payload.get("ok") is True
            and payload.get("match_type") == "template"
            and payload.get("matched_path") == "/videos/{video_id}/remix"
            and isinstance(payload.get("match"), dict)
            and payload["match"].get("category") == "local_compat_or_chatgpt_backend_bridge",
        )
        grader = {
            "type": "string_check",
            "name": "exact_label",
            "input": "{{ sample.output_text }}",
            "reference": "{{ item.label }}",
            "operation": "eq",
        }
        self.record(
            "fine_tuning_graders",
            lambda: {
                "validate": self.router.fine_tuning_graders_validate(grader),
                "pass": self.router.fine_tuning_graders_run(
                    grader,
                    model_sample="ok",
                    item={"label": "ok"},
                ),
                "fail": self.router.fine_tuning_graders_run(
                    grader,
                    model_sample="no",
                    item={"label": "ok"},
                ),
                "multi": self.router.fine_tuning_graders_run(
                    {
                        "type": "multi",
                        "name": "two_checks",
                        "graders": {
                            "exact": grader,
                            "contains": {
                                "type": "string_check",
                                "name": "contains_label",
                                "input": "{{ sample.output_text }}",
                                "reference": "{{ item.label }}",
                                "operation": "like",
                            },
                        },
                        "calculate_output": "0.5 * exact + 0.5 * contains",
                    },
                    model_sample="ok",
                    item={"label": "ok"},
                ),
            },
            lambda payload: payload["validate"].get("valid") is True
            and payload["pass"].get("reward") == 1.0
            and payload["fail"].get("reward") == 0.0
            and payload["multi"].get("reward") == 1.0,
        )
        self.record(
            "fine_tuning_jobs",
            self.fine_tuning_jobs_payload,
            lambda payload: payload["job"].get("status") == "queued"
            and payload["paused"].get("status") == "paused"
            and payload["resumed"].get("status") == "queued"
            and payload["cancelled"].get("status") == "cancelled"
            and len(payload["events"].get("data") or []) >= 4
            and len(payload["checkpoints"].get("data") or []) == 1
            and payload["permission"].get("project_id") == "proj-local-smoke"
            and len(payload["permissions"].get("data") or []) == 1
            and payload["deleted"].get("deleted") is True,
        )
        self.record(
            "organization_project_sandbox",
            self.organization_project_sandbox_payload,
            lambda payload: payload["projects"].get("object") == "list"
            and len(payload["projects"].get("data") or []) == 1
            and payload["project"].get("object") == "organization.project"
            and payload["archive"].get("status") == "archived"
            and payload["project_roles"].get("object") == "list"
            and payload["user_role_delete"].get("deleted") is True
            and payload["usage"].get("hosted_usage_report") is False
            and payload["costs"].get("hosted_cost_report") is False,
        )
        self.record(
            "videos_storyboard_sandbox",
            self.videos_storyboard_payload,
            lambda payload: payload["video"].get("hosted_video_created") is False
            and payload["retrieve"].get("id") == payload["video"].get("id")
            and payload["content_type"] == "application/json"
            and payload["content_len"] > 100
            and payload["remix"].get("operation") == "remix"
            and payload["edit"].get("operation") == "edit"
            and payload["extension"].get("operation") == "extension"
            and len(payload["characters"].get("data") or []) >= 1
            and payload["character"].get("id") == "vchar-local-default"
            and payload["deleted"].get("deleted") is True,
        )
        self.record(
            "platform_fallback_disabled",
            lambda: self.fallback_state_with_env(
                "/v1/videos/edits",
                "api_key_or_admin_key_required",
                {},
            ),
            lambda payload: payload["fallback"].get("enabled") is False
            and payload["fallback"].get("credential_env") == API_KEY_ENV
            and payload["fallback"].get("can_forward") is False,
        )
        self.record(
            "platform_fallback_enabled_api_key",
            lambda: self.fallback_state_with_env(
                "/v1/videos/edits",
                "api_key_or_admin_key_required",
                {ENABLE_ENV: "1", API_KEY_ENV: "placeholder-platform-key"},
            ),
            lambda payload: payload["fallback"].get("enabled") is True
            and payload["fallback"].get("credential_env") == API_KEY_ENV
            and payload["fallback"].get("credential_present") is True
            and payload["fallback"].get("can_forward") is True,
        )
        self.record(
            "platform_fallback_enabled_admin_key",
            lambda: self.fallback_state_with_env(
                "/v1/organization/projects",
                "api_key_or_admin_key_required",
                {ENABLE_ENV: "1", ADMIN_KEY_ENV: "placeholder-admin-key"},
            ),
            lambda payload: payload["fallback"].get("enabled") is True
            and payload["fallback"].get("credential_env") == ADMIN_KEY_ENV
            and payload["fallback"].get("admin_surface") is True
            and payload["fallback"].get("can_forward") is True,
        )
        self.record(
            "platform_fallback_enabled_access_token",
            lambda: self.fallback_state_with_env(
                "/v1/videos/edits",
                "api_key_or_admin_key_required",
                {ENABLE_ENV: "1", ACCESS_TOKEN_ENV: "placeholder-access-token"},
            ),
            lambda payload: payload["fallback"].get("enabled") is True
            and payload["fallback"].get("credential_env") == ACCESS_TOKEN_ENV
            and payload["fallback"].get("credential_present") is True
            and payload["fallback"].get("can_forward") is True,
        )
        self.record(
            "platform_fallback_prefer_mode",
            lambda: self.fallback_state_with_env(
                "/v1/responses",
                "local_compat_or_chatgpt_backend_bridge",
                {ENABLE_ENV: "1", MODE_ENV: "prefer", API_KEY_ENV: "placeholder-platform-key"},
            ),
            lambda payload: payload["fallback"].get("mode") == "prefer"
            and payload["fallback"].get("prefer_platform") is True
            and payload["fallback"].get("credential_env") == API_KEY_ENV
            and payload["fallback"].get("can_forward") is True,
        )
        store = self.router.vector_stores_create(name="offline-vector")
        item = self.router.vector_stores_add_text(
            store["id"],
            "OAuth embeddings power local search.",
            metadata={"source": "offline"},
        )
        self.record(
            "vector_stores_add_text",
            lambda: item,
            lambda payload: payload.get("object") == "oauth_compat.vector_store.item",
        )
        self.record(
            "vector_stores_search",
            lambda: self.router.vector_stores_search(store["id"], "oauth search", limit=1),
            lambda payload: len(payload.get("data") or []) == 1,
        )
        eval_obj = self.router.evals_create(
            name="offline-eval",
            data_source_config={"type": "custom", "item_schema": {}},
            testing_criteria=[{
                "type": "string_check",
                "name": "contains_expected",
                "input": "{{ output }}",
                "operation": "like",
                "reference": "offline",
            }],
            metadata={"prompt": "say offline", "expected_substring": "offline"},
        )
        eval_run = self.router.eval_runs_create(
            eval_obj["id"],
            name="offline-eval-run",
            data_source={
                "source": {
                    "content": [{
                        "item": {
                            "prompt": "say offline",
                            "expected_substring": "offline",
                        }
                    }]
                }
            },
        )
        self.record(
            "eval_runs_create",
            lambda: eval_run,
            lambda payload: payload.get("object") == "eval.run"
            and payload.get("status") == "completed",
        )
        self.record(
            "eval_output_items_list",
            lambda: self.router.eval_output_items_list(eval_obj["id"], eval_run["id"]),
            lambda payload: len(payload.get("data") or []) == 1
            and payload["data"][0].get("status") == "pass",
        )
        if write:
            self.write_reports()
        return 1 if any(row["status"] != "pass" for row in self.rows) else 0

    def write_reports(self) -> None:
        REPORTS.mkdir(exist_ok=True)
        finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        payload = {
            "finished_at": finished_at,
            "network": "not used; Codex text and embeddings are stubbed",
            "socket": "not used",
            "results": self.rows,
        }
        (REPORTS / "router_offline_smoke_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
        lines = [
            "# Router Offline Smoke Report",
            "",
            f"- Finished: `{finished_at}`",
            "- Network: not used; Codex text and embeddings are stubbed",
            "- Socket: not used",
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
        (REPORTS / "router_offline_smoke_latest.md").write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run no-network OAuth bridge router compatibility smoke tests.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/router_offline_smoke_latest.*.")
    args = parser.parse_args()
    return RouterOfflineSmoke().run(write=not args.no_write)


if __name__ == "__main__":
    raise SystemExit(main())
