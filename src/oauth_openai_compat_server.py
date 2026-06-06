from __future__ import annotations

import argparse
import base64
from email.parser import BytesParser
from email.policy import default as email_default_policy
import json
import re
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from classify_openai_path import classify as classify_openai_path
from generate_boundary_playbook import build_report as build_boundary_playbook_report
from generate_client_config import build_report as build_client_config_report
from generate_coverage_map import build_report as build_coverage_map_report
from generate_quickstart import build_report as build_quickstart_report
from generate_route_policy import build_report as build_route_policy_report
from goal_audit_report import build_report as build_goal_audit_report
from oauth_feature_router import ROOT, OAuthFeatureRouter
from generate_compatibility_guide import CATEGORY_ACTIONS
from generate_compatibility_guide import build_report as build_compatibility_guide_report
from platform_fallback import (
    credential_for_path,
    global_fallback_state,
    path_fallback_state,
    platform_base_url,
    truthy,
)
from readiness_report import build_report as build_readiness_report
from status_report import build_report as build_status_report


ARTIFACTS = ROOT / "artifacts"


def known_boundary_payload(path: str, method: str) -> tuple[Dict[str, Any], HTTPStatus]:
    if not path.startswith("/v1/"):
        return {"error": {"message": "Not found", "type": "not_found"}}, HTTPStatus.NOT_FOUND
    classified = classify_openai_path(path)
    if not classified.get("ok"):
        return {
            "error": {
                "message": "Not found in the current OpenAI surface audit.",
                "type": "not_found",
            },
            "object": "oauth_compat.not_found",
            "path": path,
            "method": method,
            "normalized_path": classified.get("normalized_path"),
            "candidates": classified.get("candidates") or [],
        }, HTTPStatus.NOT_FOUND

    match = classified.get("match") if isinstance(classified.get("match"), dict) else {}
    category = str(match.get("category") or "not_probed_directly")
    meta = CATEGORY_ACTIONS.get(category, CATEGORY_ACTIONS["not_probed_directly"])
    if category == "api_key_or_admin_key_required":
        status = HTTPStatus.FORBIDDEN
        message = "This official OpenAI path is not available through the local ChatGPT/Codex OAuth bridge."
    else:
        status = HTTPStatus.NOT_IMPLEMENTED
        message = "This OpenAI path is known, but this local OAuth bridge has no completed handler for this method/path."
    return {
        "error": {
            "message": message,
            "type": "oauth_compat_boundary",
            "code": category,
        },
        "object": "oauth_compat.boundary",
        "method": method,
        "path": path,
        "normalized_path": classified.get("normalized_path"),
        "matched_path": classified.get("matched_path"),
        "match_type": classified.get("match_type"),
        "category": category,
        "decision": meta["label"],
        "action": meta["action"],
        "support": match.get("support"),
        "evidence": match.get("evidence"),
        "platform_fallback": path_fallback_state(path, category=category),
    }, status


class CompatHandler(BaseHTTPRequestHandler):
    router: OAuthFeatureRouter

    server_version = "OAuthOpenAICompat/0.1"
    cors_allow_methods = "GET, POST, DELETE, OPTIONS"
    cors_allow_headers = (
        "Authorization, Content-Type, OpenAI-Beta, OpenAI-Organization, "
        "OpenAI-Project, X-Requested-With, X-OAuth-Compat-Prefer-Platform"
    )
    cors_expose_headers = (
        "Content-Length, Content-Type, X-OAuth-Compat-Route, X-Local-Path, "
        "X-OAuth-Platform-Credential"
    )

    def log_message(self, format: str, *args: Any) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", self.cors_allow_methods)
        self.send_header("Access-Control-Allow-Headers", self.cors_allow_headers)
        self.send_header("Access-Control-Expose-Headers", self.cors_expose_headers)
        self.send_header("Access-Control-Max-Age", "86400")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT.value)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        try:
            path = self.request_path()
            parts = self.path_parts(path)
            if self.maybe_forward_preferred_platform(path, "GET"):
                return
            if path == "/health":
                self.write_json({"ok": True, "route": "oauth_compat_server"})
                return
            if path == "/v1/oauth-capabilities":
                self.write_json(self.capabilities_payload())
                return
            if path == "/v1/oauth-readiness":
                self.write_json(self.readiness_payload())
                return
            if path == "/v1/oauth-compatibility-guide":
                self.write_json(self.compatibility_guide_payload())
                return
            if path == "/v1/oauth-client-config":
                self.write_json(self.client_config_payload())
                return
            if path == "/v1/oauth-quickstart":
                self.write_json(self.quickstart_payload())
                return
            if path == "/v1/oauth-coverage-map":
                self.write_json(self.coverage_map_payload())
                return
            if path == "/v1/oauth-route-policy":
                self.write_json(self.route_policy_payload())
                return
            if path == "/v1/oauth-boundary-playbook":
                self.write_json(self.boundary_playbook_payload())
                return
            if path == "/v1/oauth-status":
                self.write_json(self.status_payload())
                return
            if path == "/v1/oauth-goal-audit":
                self.write_json(self.goal_audit_payload())
                return
            if path == "/v1/oauth-classify":
                self.write_json(self.classify_payload())
                return
            if path == "/v1/videos":
                self.handle_videos_list()
                return
            if path == "/v1/videos/characters":
                self.handle_video_characters_list()
                return
            if parts[:2] == ["v1", "videos"] and len(parts) == 3 and parts[2] != "characters":
                self.handle_videos_retrieve(path)
                return
            if parts[:2] == ["v1", "videos"] and len(parts) == 4 and parts[3] == "content":
                self.handle_videos_content(path)
                return
            if parts[:3] == ["v1", "videos", "characters"] and len(parts) == 4:
                self.handle_video_characters_retrieve(path)
                return
            if parts[:2] == ["v1", "organization"] or parts[:2] == ["v1", "projects"]:
                self.handle_organization_sandbox(path, "GET")
                return
            if path == "/v1/skills":
                self.handle_skills_list()
                return
            if parts[:2] == ["v1", "skills"] and len(parts) == 3:
                self.handle_skills_retrieve(path)
                return
            if parts[:2] == ["v1", "skills"] and len(parts) == 4 and parts[3] == "content":
                self.handle_skill_content(path)
                return
            if parts[:2] == ["v1", "skills"] and len(parts) == 4 and parts[3] == "versions":
                self.handle_skill_versions_list(path)
                return
            if parts[:2] == ["v1", "skills"] and len(parts) == 5 and parts[3] == "versions":
                self.handle_skill_version_retrieve(path)
                return
            if parts[:2] == ["v1", "skills"] and len(parts) == 6 and parts[3] == "versions" and parts[5] == "content":
                self.handle_skill_version_content(path)
                return
            if path == "/v1/models":
                self.handle_models()
                return
            if parts[:2] == ["v1", "models"] and len(parts) == 3:
                self.handle_model_retrieve(path)
                return
            if path == "/v1/containers":
                self.handle_containers_list()
                return
            if parts[:2] == ["v1", "containers"] and len(parts) == 3:
                self.handle_containers_retrieve(path)
                return
            if parts[:2] == ["v1", "containers"] and len(parts) == 4 and parts[3] == "files":
                self.handle_container_files_list(path)
                return
            if parts[:2] == ["v1", "containers"] and len(parts) == 5 and parts[3] == "files":
                self.handle_container_files_retrieve(path)
                return
            if parts[:2] == ["v1", "containers"] and len(parts) == 6 and parts[3] == "files" and parts[5] == "content":
                self.handle_container_files_content(path)
                return
            if parts[:3] == ["v1", "chatkit", "threads"] and len(parts) == 4:
                self.handle_chatkit_threads_retrieve(path)
                return
            if parts[:3] == ["v1", "chatkit", "threads"] and len(parts) == 5 and parts[4] == "items":
                self.handle_chatkit_thread_items_list(path)
                return
            if parts[:2] == ["v1", "conversations"] and len(parts) == 3:
                self.handle_conversations_retrieve(path)
                return
            if parts[:2] == ["v1", "conversations"] and len(parts) == 4 and parts[3] == "items":
                self.handle_conversation_items_list(path)
                return
            if parts[:2] == ["v1", "conversations"] and len(parts) == 5 and parts[3] == "items":
                self.handle_conversation_items_retrieve(path)
                return
            if path == "/v1/assistants":
                self.handle_assistants_list()
                return
            if parts[:2] == ["v1", "assistants"] and len(parts) == 3:
                self.handle_assistants_retrieve(path)
                return
            if parts[:2] == ["v1", "threads"] and len(parts) == 3 and parts[2] != "runs":
                self.handle_threads_retrieve(path)
                return
            if parts[:2] == ["v1", "threads"] and len(parts) == 4 and parts[3] == "messages":
                self.handle_thread_messages_list(path)
                return
            if parts[:2] == ["v1", "threads"] and len(parts) == 5 and parts[3] == "messages":
                self.handle_thread_messages_retrieve(path)
                return
            if parts[:2] == ["v1", "threads"] and len(parts) == 4 and parts[3] == "runs":
                self.handle_thread_runs_list(path)
                return
            if parts[:2] == ["v1", "threads"] and len(parts) == 5 and parts[3] == "runs":
                self.handle_thread_runs_retrieve(path)
                return
            if parts[:2] == ["v1", "threads"] and len(parts) == 6 and parts[3] == "runs" and parts[5] == "steps":
                self.handle_thread_run_steps_list(path)
                return
            if parts[:2] == ["v1", "threads"] and len(parts) == 7 and parts[3] == "runs" and parts[5] == "steps":
                self.handle_thread_run_steps_retrieve(path)
                return
            if parts[:2] == ["v1", "responses"] and len(parts) == 4 and parts[3] == "input_items":
                self.handle_response_input_items_list(path)
                return
            if parts[:2] == ["v1", "responses"] and len(parts) == 3:
                self.handle_response_retrieve(path)
                return
            if path == "/v1/chat/completions":
                self.handle_chat_completions_list()
                return
            if parts[:3] == ["v1", "chat", "completions"] and len(parts) == 5 and parts[4] == "messages":
                self.handle_chat_completion_messages_list(path)
                return
            if parts[:3] == ["v1", "chat", "completions"] and len(parts) == 4:
                self.handle_chat_completion_retrieve(path)
                return
            if path == "/v1/audio/voices":
                self.handle_audio_voices_list()
                return
            if path == "/v1/audio/voice_consents":
                self.handle_audio_voice_consents_list()
                return
            if parts[:3] == ["v1", "audio", "voice_consents"] and len(parts) == 4:
                self.handle_audio_voice_consents_retrieve(path)
                return
            if path == "/v1/files":
                self.handle_files_list()
                return
            if parts[:2] == ["v1", "files"] and len(parts) == 4 and parts[3] == "content":
                self.handle_files_content(path)
                return
            if parts[:2] == ["v1", "files"] and len(parts) == 3:
                self.handle_files_retrieve(path)
                return
            if path == "/v1/evals":
                self.handle_evals_list()
                return
            if path == "/v1/batches":
                self.handle_batches_list()
                return
            if parts[:2] == ["v1", "batches"] and len(parts) == 3:
                self.handle_batches_retrieve(path)
                return
            if path == "/v1/fine_tuning/jobs":
                self.handle_fine_tuning_jobs_list()
                return
            if parts[:3] == ["v1", "fine_tuning", "jobs"] and len(parts) == 5 and parts[4] == "events":
                self.handle_fine_tuning_job_events_list(path)
                return
            if parts[:3] == ["v1", "fine_tuning", "jobs"] and len(parts) == 5 and parts[4] == "checkpoints":
                self.handle_fine_tuning_job_checkpoints_list(path)
                return
            if parts[:3] == ["v1", "fine_tuning", "jobs"] and len(parts) == 4:
                self.handle_fine_tuning_jobs_retrieve(path)
                return
            if parts[:3] == ["v1", "fine_tuning", "checkpoints"] and len(parts) == 5 and parts[4] == "permissions":
                self.handle_fine_tuning_checkpoint_permissions_list(path)
                return
            if parts[:2] == ["v1", "evals"] and len(parts) == 7 and parts[3] == "runs" and parts[5] == "output_items":
                self.handle_eval_output_items_retrieve(path)
                return
            if parts[:2] == ["v1", "evals"] and len(parts) == 6 and parts[3] == "runs" and parts[5] == "output_items":
                self.handle_eval_output_items_list(path)
                return
            if parts[:2] == ["v1", "evals"] and len(parts) == 5 and parts[3] == "runs":
                self.handle_eval_runs_retrieve(path)
                return
            if parts[:2] == ["v1", "evals"] and len(parts) == 4 and parts[3] == "runs":
                self.handle_eval_runs_list(path)
                return
            if parts[:2] == ["v1", "evals"] and len(parts) == 3:
                self.handle_evals_retrieve(path)
                return
            if path == "/v1/vector_stores":
                self.handle_vector_stores_list()
                return
            if parts[:2] == ["v1", "vector_stores"] and len(parts) == 6 and parts[3] == "file_batches" and parts[5] == "files":
                self.handle_vector_store_file_batches_files_list(path)
                return
            if parts[:2] == ["v1", "vector_stores"] and len(parts) == 5 and parts[3] == "file_batches":
                self.handle_vector_store_file_batches_retrieve(path)
                return
            if parts[:2] == ["v1", "vector_stores"] and len(parts) == 4 and parts[3] == "files":
                self.handle_vector_store_files_list(path)
                return
            if parts[:2] == ["v1", "vector_stores"] and len(parts) == 6 and parts[3] == "files" and parts[5] == "content":
                self.handle_vector_store_files_content(path)
                return
            if parts[:2] == ["v1", "vector_stores"] and len(parts) == 5 and parts[3] == "files":
                self.handle_vector_store_files_retrieve(path)
                return
            if parts[:2] == ["v1", "vector_stores"] and len(parts) == 3:
                self.handle_vector_stores_retrieve(path)
                return
            self.write_known_boundary_or_not_found(path, "GET")
        except FileNotFoundError as exc:
            self.write_json({
                "error": {
                    "message": str(exc)[:600],
                    "type": "not_found",
                }
            }, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.write_json({
                "error": {
                    "message": str(exc)[:600],
                    "type": type(exc).__name__,
                }
            }, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:
        try:
            path = self.request_path()
            parts = self.path_parts(path)
            if self.maybe_forward_preferred_platform(path, "POST"):
                return
            if path == "/v1/responses":
                self.handle_responses()
            elif path == "/v1/responses/compact":
                self.handle_responses_compact()
            elif path == "/v1/responses/input_tokens":
                self.handle_responses_input_tokens()
            elif parts[:2] == ["v1", "responses"] and len(parts) == 4 and parts[3] == "cancel":
                self.handle_response_cancel(path)
            elif path == "/v1/assistants":
                self.handle_assistants_create()
            elif parts[:2] == ["v1", "assistants"] and len(parts) == 3:
                self.handle_assistants_update(path)
            elif path == "/v1/threads":
                self.handle_threads_create()
            elif parts[:2] == ["v1", "threads"] and len(parts) == 3 and parts[2] == "runs":
                self.handle_threads_create_and_run()
            elif parts[:2] == ["v1", "threads"] and len(parts) == 3:
                self.handle_threads_update(path)
            elif parts[:2] == ["v1", "threads"] and len(parts) == 4 and parts[3] == "messages":
                self.handle_thread_messages_create(path)
            elif parts[:2] == ["v1", "threads"] and len(parts) == 5 and parts[3] == "messages":
                self.handle_thread_messages_update(path)
            elif parts[:2] == ["v1", "threads"] and len(parts) == 4 and parts[3] == "runs":
                self.handle_thread_runs_create(path)
            elif parts[:2] == ["v1", "threads"] and len(parts) == 6 and parts[3] == "runs" and parts[5] == "cancel":
                self.handle_thread_runs_cancel(path)
            elif parts[:2] == ["v1", "threads"] and len(parts) == 6 and parts[3] == "runs" and parts[5] == "submit_tool_outputs":
                self.handle_thread_runs_submit_tool_outputs(path)
            elif parts[:2] == ["v1", "threads"] and len(parts) == 5 and parts[3] == "runs":
                self.handle_thread_runs_update(path)
            elif path == "/v1/completions":
                self.handle_completions()
            elif path == "/v1/chat/completions":
                self.handle_chat_completions()
            elif parts[:3] == ["v1", "chat", "completions"] and len(parts) == 4:
                self.handle_chat_completion_update(path)
            elif path == "/v1/embeddings":
                self.handle_embeddings()
            elif path == "/v1/moderations":
                self.handle_moderations()
            elif path == "/v1/images/generations":
                self.handle_images_generations()
            elif path == "/v1/images/edits":
                self.handle_images_edits()
            elif path == "/v1/images/variations":
                self.handle_images_variations()
            elif path == "/v1/audio/speech":
                self.handle_audio_speech()
            elif path == "/v1/audio/transcriptions":
                self.handle_audio_transcriptions()
            elif path == "/v1/audio/translations":
                self.handle_audio_translations()
            elif path == "/v1/audio/voices":
                self.handle_audio_voices_create()
            elif path == "/v1/audio/voice_consents":
                self.handle_audio_voice_consents_create()
            elif parts[:3] == ["v1", "audio", "voice_consents"] and len(parts) == 4:
                self.handle_audio_voice_consents_update(path)
            elif path == "/v1/realtime/sessions":
                self.handle_realtime_sessions_create()
            elif path == "/v1/realtime/transcription_sessions":
                self.handle_realtime_transcription_sessions_create()
            elif parts[:3] == ["v1", "realtime", "calls"] and len(parts) == 5:
                self.handle_realtime_call_lifecycle(path)
            elif path == "/v1/files":
                self.handle_files_create()
            elif path == "/v1/skills":
                self.handle_skills_create()
            elif parts[:2] == ["v1", "skills"] and len(parts) == 3:
                self.handle_skills_update(path)
            elif parts[:2] == ["v1", "skills"] and len(parts) == 4 and parts[3] == "versions":
                self.handle_skill_versions_create(path)
            elif path == "/v1/containers":
                self.handle_containers_create()
            elif parts[:2] == ["v1", "containers"] and len(parts) == 4 and parts[3] == "files":
                self.handle_container_files_create(path)
            elif path == "/v1/chatkit/sessions":
                self.handle_chatkit_sessions_create()
            elif parts[:3] == ["v1", "chatkit", "sessions"] and len(parts) == 5 and parts[4] == "cancel":
                self.handle_chatkit_sessions_cancel(path)
            elif path == "/v1/chatkit/threads":
                self.handle_chatkit_threads_create()
            elif path == "/v1/conversations":
                self.handle_conversations_create()
            elif parts[:2] == ["v1", "conversations"] and len(parts) == 3:
                self.handle_conversations_update(path)
            elif parts[:2] == ["v1", "conversations"] and len(parts) == 4 and parts[3] == "items":
                self.handle_conversation_items_create(path)
            elif path == "/v1/uploads":
                self.handle_uploads_create()
            elif parts[:2] == ["v1", "uploads"] and len(parts) == 4 and parts[3] == "parts":
                self.handle_upload_parts_create(path)
            elif parts[:2] == ["v1", "uploads"] and len(parts) == 4 and parts[3] == "complete":
                self.handle_uploads_complete(path)
            elif parts[:2] == ["v1", "uploads"] and len(parts) == 4 and parts[3] == "cancel":
                self.handle_uploads_cancel(path)
            elif path == "/v1/batches":
                self.handle_batches_create()
            elif parts[:2] == ["v1", "batches"] and len(parts) == 4 and parts[3] == "cancel":
                self.handle_batches_cancel(path)
            elif path == "/v1/videos":
                self.handle_videos_create()
            elif path == "/v1/videos/edits":
                self.handle_videos_edits_create()
            elif path == "/v1/videos/extensions":
                self.handle_videos_extensions_create()
            elif parts[:2] == ["v1", "videos"] and len(parts) == 4 and parts[3] == "remix":
                self.handle_videos_remix(path)
            elif path == "/v1/fine_tuning/jobs":
                self.handle_fine_tuning_jobs_create()
            elif parts[:3] == ["v1", "fine_tuning", "jobs"] and len(parts) == 5 and parts[4] == "cancel":
                self.handle_fine_tuning_jobs_cancel(path)
            elif parts[:3] == ["v1", "fine_tuning", "jobs"] and len(parts) == 5 and parts[4] == "pause":
                self.handle_fine_tuning_jobs_pause(path)
            elif parts[:3] == ["v1", "fine_tuning", "jobs"] and len(parts) == 5 and parts[4] == "resume":
                self.handle_fine_tuning_jobs_resume(path)
            elif parts[:3] == ["v1", "fine_tuning", "checkpoints"] and len(parts) == 5 and parts[4] == "permissions":
                self.handle_fine_tuning_checkpoint_permissions_create(path)
            elif parts == ["v1", "fine_tuning", "alpha", "graders", "run"]:
                self.handle_fine_tuning_grader_run()
            elif parts == ["v1", "fine_tuning", "alpha", "graders", "validate"]:
                self.handle_fine_tuning_grader_validate()
            elif parts[:2] == ["v1", "organization"] or parts[:2] == ["v1", "projects"]:
                self.handle_organization_sandbox(path, "POST")
            elif path == "/v1/evals":
                self.handle_evals_create()
            elif parts[:2] == ["v1", "evals"] and len(parts) == 6 and parts[3] == "runs" and parts[5] == "cancel":
                self.handle_eval_runs_cancel(path)
            elif parts[:2] == ["v1", "evals"] and len(parts) == 5 and parts[3] == "runs":
                self.handle_eval_runs_cancel(path)
            elif parts[:2] == ["v1", "evals"] and len(parts) == 4 and parts[3] == "runs":
                self.handle_eval_runs_create(path)
            elif parts[:2] == ["v1", "evals"] and len(parts) == 3:
                self.handle_evals_update(path)
            elif path == "/v1/vector_stores":
                self.handle_vector_stores_create()
            elif parts[:2] == ["v1", "vector_stores"] and len(parts) == 4 and parts[3] == "file_batches":
                self.handle_vector_store_file_batches_create(path)
            elif parts[:2] == ["v1", "vector_stores"] and len(parts) == 6 and parts[3] == "file_batches" and parts[5] == "cancel":
                self.handle_vector_store_file_batches_cancel(path)
            elif parts[:2] == ["v1", "vector_stores"] and len(parts) == 4 and parts[3] == "files":
                self.handle_vector_store_files_create(path)
            elif parts[:2] == ["v1", "vector_stores"] and len(parts) == 4 and parts[3] == "items":
                self.handle_vector_stores_add_text(path)
            elif parts[:2] == ["v1", "vector_stores"] and len(parts) == 4 and parts[3] == "search":
                self.handle_vector_stores_search(path)
            elif path == "/v1/local/evals/text_expectation":
                self.handle_local_eval_text_expectation()
            else:
                self.write_known_boundary_or_not_found(path, "POST")
        except json.JSONDecodeError as exc:
            self.write_json({
                "error": {
                    "message": f"Invalid JSON request body: {exc.msg}",
                    "type": "bad_request",
                }
            }, HTTPStatus.BAD_REQUEST)
        except ValueError as exc:
            self.write_json({
                "error": {
                    "message": str(exc)[:600],
                    "type": "bad_request",
                }
            }, HTTPStatus.BAD_REQUEST)
        except FileNotFoundError as exc:
            self.write_json({
                "error": {
                    "message": str(exc)[:600],
                    "type": "not_found",
                }
            }, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.write_json({
                "error": {
                    "message": str(exc)[:600],
                    "type": type(exc).__name__,
                }
            }, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_DELETE(self) -> None:
        try:
            path = self.request_path()
            parts = self.path_parts(path)
            if self.maybe_forward_preferred_platform(path, "DELETE"):
                return
            if parts[:2] == ["v1", "responses"] and len(parts) == 3:
                self.handle_response_delete(path)
            elif parts[:2] == ["v1", "assistants"] and len(parts) == 3:
                self.handle_assistants_delete(path)
            elif parts[:2] == ["v1", "threads"] and len(parts) == 3:
                self.handle_threads_delete(path)
            elif parts[:2] == ["v1", "threads"] and len(parts) == 5 and parts[3] == "messages":
                self.handle_thread_messages_delete(path)
            elif parts[:3] == ["v1", "chat", "completions"] and len(parts) == 4:
                self.handle_chat_completion_delete(path)
            elif parts[:2] == ["v1", "files"] and len(parts) == 3:
                self.handle_files_delete(path)
            elif parts[:3] == ["v1", "audio", "voice_consents"] and len(parts) == 4:
                self.handle_audio_voice_consents_delete(path)
            elif parts[:2] == ["v1", "skills"] and len(parts) == 3:
                self.handle_skills_delete(path)
            elif parts[:2] == ["v1", "skills"] and len(parts) == 5 and parts[3] == "versions":
                self.handle_skill_version_delete(path)
            elif parts[:2] == ["v1", "conversations"] and len(parts) == 3:
                self.handle_conversations_delete(path)
            elif parts[:2] == ["v1", "conversations"] and len(parts) == 5 and parts[3] == "items":
                self.handle_conversation_items_delete(path)
            elif parts[:2] == ["v1", "containers"] and len(parts) == 3:
                self.handle_containers_delete(path)
            elif parts[:2] == ["v1", "videos"] and len(parts) == 3:
                self.handle_videos_delete(path)
            elif parts[:2] == ["v1", "evals"] and len(parts) == 5 and parts[3] == "runs":
                self.handle_eval_runs_delete(path)
            elif parts[:2] == ["v1", "evals"] and len(parts) == 3:
                self.handle_evals_delete(path)
            elif parts[:3] == ["v1", "fine_tuning", "checkpoints"] and len(parts) == 6 and parts[4] == "permissions":
                self.handle_fine_tuning_checkpoint_permissions_delete(path)
            elif parts[:2] == ["v1", "organization"] or parts[:2] == ["v1", "projects"]:
                self.handle_organization_sandbox(path, "DELETE")
            elif parts[:2] == ["v1", "vector_stores"] and len(parts) == 5 and parts[3] == "files":
                self.handle_vector_store_files_delete(path)
            elif parts[:2] == ["v1", "vector_stores"] and len(parts) == 3:
                self.handle_vector_stores_delete(path)
            else:
                self.write_known_boundary_or_not_found(path, "DELETE")
        except FileNotFoundError as exc:
            self.write_json({
                "error": {
                    "message": str(exc)[:600],
                    "type": "not_found",
                }
            }, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.write_json({
                "error": {
                    "message": str(exc)[:600],
                    "type": type(exc).__name__,
                }
            }, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_models(self) -> None:
        now = int(time.time())
        self.write_json({
            "object": "list",
            "data": [
                self.model_shape(model_id, created=now)
                for model_id in self.router.oauth.model_ids
            ],
            "oauth_compat_route": "codex_models",
        })

    def handle_model_retrieve(self, path: str) -> None:
        model_id = self.path_part(path, 3)
        if model_id not in self.router.oauth.model_ids:
            raise FileNotFoundError(f"Unknown local model: {model_id}")
        self.write_json(self.model_shape(model_id))

    def handle_responses(self) -> None:
        body = self.read_json()
        input_value = body.get("input", "")
        prompt = self.input_to_text(input_value)
        instructions = body.get("instructions") if isinstance(body.get("instructions"), str) else "Answer directly."
        result = self.router.responses_create(prompt, instructions=instructions)
        response_id = f"resp_oauth_{uuid.uuid4().hex}"
        text = result.get("output_text", "")
        payload = {
            "id": response_id,
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
            "parallel_tool_calls": False,
            "tool_choice": "auto",
            "tools": [],
            "status": "completed",
        }
        input_items = [self.response_input_item_shape(input_value, prompt)]
        self.router.responses_save(payload, input_items)
        if body.get("stream") is True:
            self.write_response_stream(payload)
            return
        self.write_json(payload)

    def handle_responses_input_tokens(self) -> None:
        body = self.read_json()
        payload = self.router.responses_input_tokens_estimate(
            body.get("input", ""),
            instructions=body.get("instructions") if isinstance(body.get("instructions"), str) else None,
        )
        self.write_json({
            "object": payload.get("object"),
            "input_tokens": payload.get("input_tokens"),
            "cached_input_tokens": payload.get("cached_input_tokens"),
            "total_tokens": payload.get("total_tokens"),
            "estimated": payload.get("estimated"),
            "method": payload.get("method"),
            "text_chars": payload.get("text_chars"),
            "text_words": payload.get("text_words"),
            "oauth_compat_route": payload.get("route"),
        })

    def handle_responses_compact(self) -> None:
        body = self.read_json()
        payload = self.router.responses_compact(
            body.get("input", ""),
            instructions=body.get("instructions") if isinstance(body.get("instructions"), str) else None,
        )
        self.write_json({
            "id": f"cmpct_oauth_{uuid.uuid4().hex}",
            "object": "response.compaction",
            "created_at": int(time.time()),
            "output": [{
                "id": f"cmpct_item_{uuid.uuid4().hex}",
                "type": "compaction",
                "encrypted_content": payload.get("encrypted_content"),
                "created_by": "oauth-local-compat",
                "local_compacted_text": payload.get("compacted_text"),
            }],
            "usage": payload.get("usage"),
            "model": payload.get("model"),
            "estimated": True,
            "oauth_compat_route": payload.get("route"),
        })

    def handle_response_retrieve(self, path: str) -> None:
        response_id = self.path_part(path, 3)
        payload = self.router.responses_retrieve(response_id)
        if "stream=true" in self.path:
            self.write_response_stream(payload)
            return
        self.write_json(payload)

    def handle_response_cancel(self, path: str) -> None:
        response_id = self.path_part(path, 3)
        self.write_json(self.router.responses_cancel(response_id))

    def handle_response_delete(self, path: str) -> None:
        response_id = self.path_part(path, 3)
        self.router.responses_delete(response_id)
        self.write_empty(HTTPStatus.NO_CONTENT)

    def handle_response_input_items_list(self, path: str) -> None:
        response_id = self.path_part(path, 3)
        payload = self.router.response_input_items_list(response_id)
        self.write_json({
            "object": "list",
            "data": payload.get("data", []),
            "oauth_compat_route": payload.get("route"),
        })

    def handle_completions(self) -> None:
        body = self.read_json()
        if "prompt" not in body:
            raise ValueError("prompt is required")
        prompt = self.input_to_text(body.get("prompt"))
        result = self.router.completions_create(prompt)
        payload = {
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
        if body.get("stream") is True:
            self.write_completion_stream(payload)
            return
        self.write_json(payload)

    def handle_chat_completions(self) -> None:
        body = self.read_json()
        messages = body.get("messages")
        if not isinstance(messages, list):
            raise ValueError("messages must be a list")
        result = self.router.chat_completions_create(messages)
        message = result.get("message", {"role": "assistant", "content": ""})
        payload = {
            "id": f"chatcmpl_oauth_{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": result.get("model"),
            "choices": [{
                "index": 0,
                "message": message,
                "finish_reason": "stop",
            }],
            "oauth_compat_route": result.get("route"),
        }
        self.router.chat_completions_save(payload, messages, message if isinstance(message, dict) else {})
        if body.get("stream") is True:
            self.write_chat_stream(payload)
            return
        self.write_json(payload)

    def handle_chat_completion_retrieve(self, path: str) -> None:
        completion_id = self.path_part(path, 4)
        self.write_json(self.router.chat_completions_retrieve(completion_id))

    def handle_chat_completions_list(self) -> None:
        payload = self.router.chat_completions_list()
        self.write_json({
            "object": "list",
            "data": payload.get("data", []),
            "oauth_compat_route": payload.get("route"),
        })

    def handle_chat_completion_update(self, path: str) -> None:
        completion_id = self.path_part(path, 4)
        body = self.read_json()
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        self.write_json(self.router.chat_completions_update(completion_id, metadata=metadata))

    def handle_chat_completion_delete(self, path: str) -> None:
        completion_id = self.path_part(path, 4)
        self.write_json(self.router.chat_completions_delete(completion_id))

    def handle_chat_completion_messages_list(self, path: str) -> None:
        completion_id = self.path_part(path, 4)
        payload = self.router.chat_completion_messages_list(completion_id)
        self.write_json({
            "object": "list",
            "data": payload.get("data", []),
            "oauth_compat_route": payload.get("route"),
        })

    def handle_assistants_create(self) -> None:
        body = self.read_json()
        model = body.get("model")
        if not isinstance(model, str) or not model:
            raise ValueError("model must be a non-empty string")
        self.write_json(self.router.assistants_create(
            model=model,
            name=body.get("name") if isinstance(body.get("name"), str) else None,
            description=body.get("description") if isinstance(body.get("description"), str) else None,
            instructions=body.get("instructions") if isinstance(body.get("instructions"), str) else None,
            tools=body.get("tools") if isinstance(body.get("tools"), list) else None,
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
        ))

    def handle_assistants_list(self) -> None:
        payload = self.router.assistants_list()
        self.write_json({"object": "list", "data": payload.get("data", []), "oauth_compat_route": payload.get("route")})

    def handle_assistants_retrieve(self, path: str) -> None:
        self.write_json(self.router.assistants_retrieve(self.path_part(path, 3)))

    def handle_assistants_update(self, path: str) -> None:
        body = self.read_json()
        self.write_json(self.router.assistants_update(
            self.path_part(path, 3),
            model=body.get("model") if isinstance(body.get("model"), str) else None,
            name=body.get("name") if isinstance(body.get("name"), str) else None,
            description=body.get("description") if isinstance(body.get("description"), str) else None,
            instructions=body.get("instructions") if isinstance(body.get("instructions"), str) else None,
            tools=body.get("tools") if isinstance(body.get("tools"), list) else None,
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
        ))

    def handle_assistants_delete(self, path: str) -> None:
        self.write_json(self.router.assistants_delete(self.path_part(path, 3)))

    def handle_threads_create(self) -> None:
        body = self.read_json()
        self.write_json(self.router.threads_create(
            messages=body.get("messages") if isinstance(body.get("messages"), list) else None,
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
            tool_resources=body.get("tool_resources") if isinstance(body.get("tool_resources"), dict) else None,
        ))

    def handle_threads_retrieve(self, path: str) -> None:
        self.write_json(self.router.threads_retrieve(self.path_part(path, 3)))

    def handle_threads_update(self, path: str) -> None:
        body = self.read_json()
        self.write_json(self.router.threads_update(
            self.path_part(path, 3),
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
            tool_resources=body.get("tool_resources") if isinstance(body.get("tool_resources"), dict) else None,
        ))

    def handle_threads_delete(self, path: str) -> None:
        self.write_json(self.router.threads_delete(self.path_part(path, 3)))

    def handle_thread_messages_create(self, path: str) -> None:
        body = self.read_json()
        role = body.get("role")
        if not isinstance(role, str) or not role:
            raise ValueError("role must be a non-empty string")
        if "content" not in body:
            raise ValueError("content is required")
        self.write_json(self.router.thread_messages_create(
            self.path_part(path, 3),
            role=role,
            content=body.get("content"),
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
            attachments=body.get("attachments") if isinstance(body.get("attachments"), list) else None,
        ))

    def handle_thread_messages_list(self, path: str) -> None:
        payload = self.router.thread_messages_list(self.path_part(path, 3))
        self.write_json({"object": "list", "data": payload.get("data", []), "oauth_compat_route": payload.get("route")})

    def handle_thread_messages_retrieve(self, path: str) -> None:
        self.write_json(self.router.thread_messages_retrieve(self.path_part(path, 3), self.path_part(path, 5)))

    def handle_thread_messages_update(self, path: str) -> None:
        body = self.read_json()
        self.write_json(self.router.thread_messages_update(
            self.path_part(path, 3),
            self.path_part(path, 5),
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
        ))

    def handle_thread_messages_delete(self, path: str) -> None:
        self.write_json(self.router.thread_messages_delete(self.path_part(path, 3), self.path_part(path, 5)))

    def handle_thread_runs_create(self, path: str) -> None:
        body = self.read_json()
        assistant_id = body.get("assistant_id")
        if not isinstance(assistant_id, str) or not assistant_id:
            raise ValueError("assistant_id must be a non-empty string")
        self.write_json(self.router.thread_runs_create(
            self.path_part(path, 3),
            assistant_id=assistant_id,
            instructions=body.get("instructions") if isinstance(body.get("instructions"), str) else None,
            additional_instructions=body.get("additional_instructions") if isinstance(body.get("additional_instructions"), str) else None,
            additional_messages=body.get("additional_messages") if isinstance(body.get("additional_messages"), list) else None,
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
            model=body.get("model") if isinstance(body.get("model"), str) else None,
        ))

    def handle_threads_create_and_run(self) -> None:
        body = self.read_json()
        assistant_id = body.get("assistant_id")
        if not isinstance(assistant_id, str) or not assistant_id:
            raise ValueError("assistant_id must be a non-empty string")
        self.write_json(self.router.threads_create_and_run(
            assistant_id=assistant_id,
            thread=body.get("thread") if isinstance(body.get("thread"), dict) else None,
            instructions=body.get("instructions") if isinstance(body.get("instructions"), str) else None,
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
            model=body.get("model") if isinstance(body.get("model"), str) else None,
        ))

    def handle_thread_runs_list(self, path: str) -> None:
        payload = self.router.thread_runs_list(self.path_part(path, 3))
        self.write_json({"object": "list", "data": payload.get("data", []), "oauth_compat_route": payload.get("route")})

    def handle_thread_runs_retrieve(self, path: str) -> None:
        self.write_json(self.router.thread_runs_retrieve(self.path_part(path, 3), self.path_part(path, 5)))

    def handle_thread_runs_update(self, path: str) -> None:
        body = self.read_json()
        self.write_json(self.router.thread_runs_update(
            self.path_part(path, 3),
            self.path_part(path, 5),
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
        ))

    def handle_thread_runs_cancel(self, path: str) -> None:
        self.write_json(self.router.thread_runs_cancel(self.path_part(path, 3), self.path_part(path, 5)))

    def handle_thread_runs_submit_tool_outputs(self, path: str) -> None:
        body = self.read_json()
        tool_outputs = body.get("tool_outputs") if isinstance(body.get("tool_outputs"), list) else []
        self.write_json(self.router.thread_runs_submit_tool_outputs(
            self.path_part(path, 3),
            self.path_part(path, 5),
            tool_outputs=tool_outputs,
        ))

    def handle_thread_run_steps_list(self, path: str) -> None:
        payload = self.router.thread_run_steps_list(self.path_part(path, 3), self.path_part(path, 5))
        self.write_json({"object": "list", "data": payload.get("data", []), "oauth_compat_route": payload.get("route")})

    def handle_thread_run_steps_retrieve(self, path: str) -> None:
        self.write_json(self.router.thread_run_steps_retrieve(self.path_part(path, 3), self.path_part(path, 5), self.path_part(path, 7)))

    def handle_embeddings(self) -> None:
        body = self.read_json()
        input_value = body.get("input")
        text = self.input_to_text(input_value)
        payload = self.router.embeddings_create(text)
        self.write_json(payload, HTTPStatus.OK if payload.get("_http_status", 200) < 400 else HTTPStatus.BAD_GATEWAY)

    def handle_images_generations(self) -> None:
        body = self.read_json()
        prompt = body.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        size = body.get("size", "1024x1024")
        if size not in {"1024x1024", "1536x1024", "1024x1536", "auto"}:
            raise ValueError("size must be one of 1024x1024, 1536x1024, 1024x1536, auto")
        ARTIFACTS.mkdir(exist_ok=True)
        output_path = ARTIFACTS / f"compat_proxy_image_{uuid.uuid4().hex}.png"
        result = self.router.images_generate(prompt, output_path, size=size)
        self.write_image_result(result, response_format=body.get("response_format"))

    def handle_images_edits(self) -> None:
        fields, files = self.read_multipart_form()
        file_item = files.get("image")
        if not file_item:
            raise ValueError("multipart field 'image' is required")
        prompt = fields.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        size = fields.get("size") or "1024x1024"
        if size not in {"1024x1024", "1536x1024", "1024x1536", "auto"}:
            raise ValueError("size must be one of 1024x1024, 1536x1024, 1024x1536, auto")
        image_path = self.write_uploaded_file(file_item)
        ARTIFACTS.mkdir(exist_ok=True)
        output_path = ARTIFACTS / f"compat_proxy_image_edit_{uuid.uuid4().hex}.png"
        result = self.router.images_edit(image_path, prompt, output_path, size=size)
        self.write_image_result(result, response_format=fields.get("response_format"))

    def handle_images_variations(self) -> None:
        fields, files = self.read_multipart_form()
        file_item = files.get("image")
        if not file_item:
            raise ValueError("multipart field 'image' is required")
        size = fields.get("size") or "1024x1024"
        if size not in {"1024x1024", "1536x1024", "1024x1536", "auto"}:
            raise ValueError("size must be one of 1024x1024, 1536x1024, 1024x1536, auto")
        image_path = self.write_uploaded_file(file_item)
        ARTIFACTS.mkdir(exist_ok=True)
        output_path = ARTIFACTS / f"compat_proxy_image_variation_{uuid.uuid4().hex}.png"
        result = self.router.images_variation(image_path, output_path, size=size)
        self.write_image_result(result, response_format=fields.get("response_format"))

    def write_image_result(self, result: Dict[str, Any], *, response_format: Any = None) -> None:
        image_bytes = Path(result["path"]).read_bytes()
        item: Dict[str, Any]
        if response_format == "url":
            item = {"url": f"file://{result['path']}"}
        else:
            item = {"b64_json": base64.b64encode(image_bytes).decode("ascii")}
        self.write_json({
            "created": int(time.time()),
            "data": [item],
            "oauth_compat_route": result.get("route"),
            "size": result.get("size"),
            "local_path": result.get("path"),
            "source_description_chars": result.get("source_description_chars"),
        })

    def handle_moderations(self) -> None:
        body = self.read_json()
        if "input" not in body:
            raise ValueError("input is required")
        model = body.get("model") if isinstance(body.get("model"), str) else "local-heuristic-moderation"
        payload = self.router.moderations_create(body.get("input"), model=model)
        payload["oauth_compat_route"] = payload.pop("route", "local_heuristic_moderation")
        self.write_json(payload)

    def handle_audio_speech(self) -> None:
        body = self.read_json()
        text = body.get("input")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("input must be a non-empty string")
        ARTIFACTS.mkdir(exist_ok=True)
        output_path = ARTIFACTS / f"compat_proxy_audio_{uuid.uuid4().hex}.pcm16"
        result = self.router.audio_speech_create(text, output_path, voice=body.get("voice"))
        audio_bytes = Path(result["path"]).read_bytes()
        headers = {
            "X-OAuth-Compat-Route": str(result.get("route")),
            "X-Local-Path": str(result.get("path")),
            "X-OAuth-Compat-Fallback": "true" if result.get("fallback") else "false",
        }
        if result.get("realtime_error_type"):
            headers["X-OAuth-Compat-Upstream-Error-Type"] = str(result.get("realtime_error_type"))
        self.write_bytes(
            audio_bytes,
            content_type="audio/L16; rate=24000; channels=1",
            headers=headers,
        )

    def handle_audio_transcriptions(self) -> None:
        _fields, files = self.read_multipart_form()
        file_item = files.get("file")
        if not file_item:
            raise ValueError("multipart field 'file' is required")
        path = self.write_uploaded_file(file_item)
        payload = self.router.audio_transcriptions_create(path)
        self.write_json(payload, HTTPStatus.OK if payload.get("_http_status", 200) < 400 else HTTPStatus.BAD_GATEWAY)

    def handle_audio_translations(self) -> None:
        fields, files = self.read_multipart_form()
        file_item = files.get("file")
        if not file_item:
            raise ValueError("multipart field 'file' is required")
        path = self.write_uploaded_file(file_item)
        payload = self.router.audio_translations_create(path, prompt=fields.get("prompt"))
        self.write_json(payload, HTTPStatus.OK if payload.get("_http_status", 200) < 400 else HTTPStatus.BAD_GATEWAY)

    def handle_audio_voices_list(self) -> None:
        self.write_json(self.router.audio_voices_list())

    def handle_audio_voices_create(self) -> None:
        fields, files = self.read_multipart_form()
        sample = files.get("audio_sample")
        if not sample:
            raise ValueError("multipart field 'audio_sample' is required")
        name = fields.get("name")
        consent = fields.get("consent")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        if not isinstance(consent, str) or not consent.strip():
            raise ValueError("consent must be a non-empty string")
        sample_path = self.write_uploaded_file(sample)
        self.write_json(self.router.audio_voices_create(
            name=name,
            consent=consent,
            audio_sample_path=sample_path,
            mime_type=str(sample.get("content_type") or "application/octet-stream"),
        ))

    def handle_audio_voice_consents_create(self) -> None:
        fields, files = self.read_multipart_form()
        recording = files.get("recording")
        if not recording:
            raise ValueError("multipart field 'recording' is required")
        name = fields.get("name")
        language = fields.get("language")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        if not isinstance(language, str) or not language.strip():
            raise ValueError("language must be a non-empty string")
        recording_path = self.write_uploaded_file(recording)
        self.write_json(self.router.audio_voice_consents_create(
            name=name,
            language=language,
            recording_path=recording_path,
            mime_type=str(recording.get("content_type") or "application/octet-stream"),
        ))

    def handle_audio_voice_consents_list(self) -> None:
        self.write_json(self.router.audio_voice_consents_list())

    def handle_audio_voice_consents_retrieve(self, path: str) -> None:
        self.write_json(self.router.audio_voice_consents_retrieve(self.path_part(path, 4)))

    def handle_audio_voice_consents_update(self, path: str) -> None:
        body = self.read_json()
        name = body.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        self.write_json(self.router.audio_voice_consents_update(self.path_part(path, 4), name=name))

    def handle_audio_voice_consents_delete(self, path: str) -> None:
        self.write_json(self.router.audio_voice_consents_delete(self.path_part(path, 4)))

    def handle_realtime_sessions_create(self) -> None:
        body = self.read_json()
        payload = self.router.realtime_sessions_create(body)
        self.write_json(payload, HTTPStatus.OK if payload.get("_http_status", 200) < 400 else HTTPStatus.BAD_GATEWAY)

    def handle_realtime_transcription_sessions_create(self) -> None:
        body = self.read_json()
        payload = self.router.realtime_transcription_sessions_create(body)
        self.write_json(payload, HTTPStatus.OK if payload.get("_http_status", 200) < 400 else HTTPStatus.BAD_GATEWAY)

    def handle_realtime_call_lifecycle(self, path: str) -> None:
        parts = self.path_parts(path)
        body = self.read_json()
        payload = self.router.realtime_call_lifecycle(parts[3], parts[4], body)
        self.write_json(payload)

    def handle_files_create(self) -> None:
        fields, files = self.read_multipart_form()
        file_item = files.get("file")
        if not file_item:
            raise ValueError("multipart field 'file' is required")
        purpose = fields.get("purpose") or "assistants"
        path = self.write_uploaded_file(file_item)
        result = self.router.files_create(path, purpose=purpose)
        self.write_json(self.openai_file_shape(result), HTTPStatus.OK if result.get("_http_status", 200) < 400 else HTTPStatus.BAD_GATEWAY)

    def handle_files_list(self) -> None:
        payload = self.router.files_list()
        self.write_json({
            "object": "list",
            "data": [self.openai_file_shape(item) for item in payload.get("data", [])],
            "oauth_compat_route": payload.get("route"),
        })

    def handle_files_retrieve(self, path: str) -> None:
        file_id = self.path_part(path, 3)
        self.write_json(self.openai_file_shape(self.router.files_retrieve(file_id)))

    def handle_files_content(self, path: str) -> None:
        file_id = self.path_part(path, 3)
        content, content_type, record = self.router.files_content(file_id)
        self.write_bytes(
            content,
            content_type=content_type,
            headers={"X-OAuth-Compat-Route": str(record.get("route"))},
        )

    def handle_files_delete(self, path: str) -> None:
        file_id = self.path_part(path, 3)
        self.write_json(self.router.files_delete(file_id))

    def handle_skills_create(self) -> None:
        body, file_item = self.read_json_or_multipart()
        metadata = self.object_field(body, "metadata")
        description = body.get("description") if isinstance(body.get("description"), str) else None
        content = (
            body.get("content")
            if isinstance(body.get("content"), str)
            else body.get("instructions")
            if isinstance(body.get("instructions"), str)
            else None
        )
        bundle_bytes = file_item.get("data") if isinstance(file_item, dict) and isinstance(file_item.get("data"), bytes) else None
        filename = file_item.get("filename") if isinstance(file_item, dict) and isinstance(file_item.get("filename"), str) else None
        self.write_json(self.router.skills_create(
            name=body.get("name") if isinstance(body.get("name"), str) else None,
            description=description,
            content=content,
            metadata=metadata,
            bundle_bytes=bundle_bytes,
            filename=filename,
        ))

    def handle_skills_list(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        limit = self.int_query(query, "limit", 100)
        order = query.get("order", ["desc"])[0]
        after = query.get("after", [None])[0]
        self.write_json(self.router.skills_list(limit=limit, order=order, after=after))

    def handle_skills_retrieve(self, path: str) -> None:
        self.write_json(self.router.skills_retrieve(self.path_part(path, 3)))

    def handle_skills_update(self, path: str) -> None:
        body = self.read_json()
        default_version = body.get("default_version")
        if not isinstance(default_version, str) or not default_version:
            raise ValueError("default_version must be a non-empty string")
        self.write_json(self.router.skills_update_default_version(
            self.path_part(path, 3),
            default_version=default_version,
        ))

    def handle_skills_delete(self, path: str) -> None:
        self.write_json(self.router.skills_delete(self.path_part(path, 3)))

    def handle_skill_content(self, path: str) -> None:
        skill_id = self.path_part(path, 3)
        content, content_type, record = self.router.skill_content(skill_id)
        self.write_bytes(
            content,
            content_type=content_type,
            headers={
                "X-OAuth-Compat-Route": "local_skill_registry",
                "Content-Disposition": f'attachment; filename="{skill_id}.zip"',
                "X-Local-Skill-Version": str(record.get("version") or ""),
            },
        )

    def handle_skill_versions_create(self, path: str) -> None:
        body, file_item = self.read_json_or_multipart()
        metadata = self.object_field(body, "metadata")
        content = (
            body.get("content")
            if isinstance(body.get("content"), str)
            else body.get("instructions")
            if isinstance(body.get("instructions"), str)
            else None
        )
        bundle_bytes = file_item.get("data") if isinstance(file_item, dict) and isinstance(file_item.get("data"), bytes) else None
        filename = file_item.get("filename") if isinstance(file_item, dict) and isinstance(file_item.get("filename"), str) else None
        self.write_json(self.router.skill_versions_create(
            self.path_part(path, 3),
            content=content,
            description=body.get("description") if isinstance(body.get("description"), str) else None,
            metadata=metadata,
            bundle_bytes=bundle_bytes,
            filename=filename,
        ))

    def handle_skill_versions_list(self, path: str) -> None:
        query = parse_qs(urlparse(self.path).query)
        limit = self.int_query(query, "limit", 100)
        order = query.get("order", ["desc"])[0]
        after = query.get("after", [None])[0]
        self.write_json(self.router.skill_versions_list(
            self.path_part(path, 3),
            limit=limit,
            order=order,
            after=after,
        ))

    def handle_skill_version_retrieve(self, path: str) -> None:
        self.write_json(self.router.skill_version_retrieve(self.path_part(path, 3), self.path_part(path, 5)))

    def handle_skill_version_delete(self, path: str) -> None:
        self.write_json(self.router.skill_version_delete(self.path_part(path, 3), self.path_part(path, 5)))

    def handle_skill_version_content(self, path: str) -> None:
        skill_id = self.path_part(path, 3)
        version = self.path_part(path, 5)
        content, content_type, record = self.router.skill_version_content(skill_id, version)
        self.write_bytes(
            content,
            content_type=content_type,
            headers={
                "X-OAuth-Compat-Route": "local_skill_registry",
                "Content-Disposition": f'attachment; filename="{skill_id}-{version}.zip"',
                "X-Local-Skill-Version": str(record.get("version") or ""),
            },
        )

    def handle_containers_create(self) -> None:
        body = self.read_json()
        name = body.get("name") if isinstance(body.get("name"), str) else None
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        expires_after = body.get("expires_after") if isinstance(body.get("expires_after"), dict) else None
        self.write_json(self.openai_container_shape(self.router.containers_create(
            name=name,
            metadata=metadata,
            expires_after=expires_after,
        )))

    def handle_containers_list(self) -> None:
        payload = self.router.containers_list()
        self.write_json({
            "object": "list",
            "data": [self.openai_container_shape(item) for item in payload.get("data", [])],
            "oauth_compat_route": payload.get("route"),
        })

    def handle_containers_retrieve(self, path: str) -> None:
        container_id = self.path_part(path, 3)
        self.write_json(self.openai_container_shape(self.router.containers_retrieve(container_id)))

    def handle_containers_delete(self, path: str) -> None:
        container_id = self.path_part(path, 3)
        self.write_json(self.router.containers_delete(container_id))

    def handle_chatkit_sessions_create(self) -> None:
        body = self.read_json()
        model = body.get("model") if isinstance(body.get("model"), str) else None
        thread_id = body.get("thread_id") if isinstance(body.get("thread_id"), str) else None
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        self.write_json(self.router.chatkit_sessions_create(
            model=model,
            thread_id=thread_id,
            metadata=metadata,
        ))

    def handle_chatkit_sessions_cancel(self, path: str) -> None:
        session_id = self.path_part(path, 4)
        self.write_json(self.router.chatkit_sessions_cancel(session_id))

    def handle_chatkit_threads_create(self) -> None:
        body = self.read_json()
        items = body.get("items") if isinstance(body.get("items"), list) else None
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        self.write_json(self.router.chatkit_threads_create(items=items, metadata=metadata))

    def handle_chatkit_threads_retrieve(self, path: str) -> None:
        thread_id = self.path_part(path, 4)
        self.write_json(self.router.chatkit_threads_retrieve(thread_id))

    def handle_chatkit_thread_items_list(self, path: str) -> None:
        thread_id = self.path_part(path, 4)
        self.write_json(self.router.chatkit_thread_items_list(thread_id))

    def handle_conversations_create(self) -> None:
        body = self.read_json()
        items = body.get("items") if isinstance(body.get("items"), list) else None
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        self.write_json(self.router.conversations_create(items=items, metadata=metadata))

    def handle_conversations_retrieve(self, path: str) -> None:
        self.write_json(self.router.conversations_retrieve(self.path_part(path, 3)))

    def handle_conversations_update(self, path: str) -> None:
        body = self.read_json()
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        self.write_json(self.router.conversations_update(self.path_part(path, 3), metadata=metadata))

    def handle_conversations_delete(self, path: str) -> None:
        self.write_json(self.router.conversations_delete(self.path_part(path, 3)))

    def handle_conversation_items_create(self, path: str) -> None:
        body = self.read_json()
        items = body.get("items")
        if not isinstance(items, list):
            raise ValueError("items must be an array")
        self.write_json(self.router.conversation_items_create(self.path_part(path, 3), items=items))

    def handle_conversation_items_list(self, path: str) -> None:
        query = parse_qs(urlparse(self.path).query)
        self.write_json(self.router.conversation_items_list(
            self.path_part(path, 3),
            limit=self.int_query(query, "limit", 20),
            order=query.get("order", ["desc"])[0],
            after=query.get("after", [None])[0],
        ))

    def handle_conversation_items_retrieve(self, path: str) -> None:
        self.write_json(self.router.conversation_items_retrieve(self.path_part(path, 3), self.path_part(path, 5)))

    def handle_conversation_items_delete(self, path: str) -> None:
        self.write_json(self.router.conversation_items_delete(self.path_part(path, 3), self.path_part(path, 5)))

    def handle_container_files_create(self, path: str) -> None:
        container_id = self.path_part(path, 3)
        fields, files = self.read_multipart_form()
        file_item = files.get("file")
        if not file_item:
            raise ValueError("multipart field 'file' is required")
        local_path = self.write_uploaded_file(file_item)
        self.write_json(self.openai_container_file_shape(self.router.container_files_create(
            container_id,
            local_path,
            filename=fields.get("filename") or str(file_item.get("filename") or ""),
            mime_type=str(file_item.get("content_type") or "application/octet-stream"),
        )))

    def handle_container_files_list(self, path: str) -> None:
        container_id = self.path_part(path, 3)
        payload = self.router.container_files_list(container_id)
        self.write_json({
            "object": "list",
            "data": [self.openai_container_file_shape(item) for item in payload.get("data", [])],
            "oauth_compat_route": payload.get("route"),
        })

    def handle_container_files_retrieve(self, path: str) -> None:
        container_id = self.path_part(path, 3)
        file_id = self.path_part(path, 5)
        self.write_json(self.openai_container_file_shape(self.router.container_files_retrieve(container_id, file_id)))

    def handle_container_files_content(self, path: str) -> None:
        container_id = self.path_part(path, 3)
        file_id = self.path_part(path, 5)
        content, content_type, record = self.router.container_files_content(container_id, file_id)
        self.write_bytes(
            content,
            content_type=content_type,
            headers={"X-OAuth-Compat-Route": str(record.get("route"))},
        )

    def handle_uploads_create(self) -> None:
        body = self.read_json()
        byte_count = body.get("bytes")
        filename = body.get("filename")
        mime_type = body.get("mime_type")
        purpose = body.get("purpose")
        if not isinstance(byte_count, int):
            raise ValueError("bytes must be an integer")
        if not isinstance(filename, str) or not filename:
            raise ValueError("filename must be a non-empty string")
        if not isinstance(mime_type, str) or not mime_type:
            raise ValueError("mime_type must be a non-empty string")
        if not isinstance(purpose, str) or not purpose:
            raise ValueError("purpose must be a non-empty string")
        expires_after = body.get("expires_after") if isinstance(body.get("expires_after"), dict) else None
        self.write_json(self.openai_upload_shape(self.router.uploads_create(
            bytes=byte_count,
            filename=filename,
            mime_type=mime_type,
            purpose=purpose,
            expires_after=expires_after,
        )))

    def handle_upload_parts_create(self, path: str) -> None:
        upload_id = self.path_part(path, 3)
        fields, files = self.read_multipart_form()
        item = files.get("data")
        if item:
            data = item.get("data")
        elif "data" in fields:
            data = fields["data"].encode("utf-8")
        else:
            raise ValueError("multipart field 'data' is required")
        if not isinstance(data, bytes):
            raise ValueError("multipart field 'data' must contain bytes")
        self.write_json(self.openai_upload_part_shape(self.router.upload_parts_create(upload_id, data)))

    def handle_uploads_complete(self, path: str) -> None:
        upload_id = self.path_part(path, 3)
        body = self.read_json()
        part_ids = body.get("part_ids")
        if not isinstance(part_ids, list) or not all(isinstance(part_id, str) and part_id for part_id in part_ids):
            raise ValueError("part_ids must be a list of non-empty strings")
        md5 = body.get("md5") if isinstance(body.get("md5"), str) else None
        self.write_json(self.openai_upload_shape(self.router.uploads_complete(upload_id, part_ids, md5=md5)))

    def handle_uploads_cancel(self, path: str) -> None:
        upload_id = self.path_part(path, 3)
        self.write_json(self.openai_upload_shape(self.router.uploads_cancel(upload_id)))

    def handle_batches_create(self) -> None:
        body = self.read_json()
        input_file_id = body.get("input_file_id")
        endpoint = body.get("endpoint")
        completion_window = body.get("completion_window")
        if not isinstance(input_file_id, str) or not input_file_id:
            raise ValueError("input_file_id must be a non-empty string")
        if not isinstance(endpoint, str) or not endpoint:
            raise ValueError("endpoint must be a non-empty string")
        if not isinstance(completion_window, str) or not completion_window:
            raise ValueError("completion_window must be a non-empty string")
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        output_expires_after = body.get("output_expires_after") if isinstance(body.get("output_expires_after"), dict) else None
        self.write_json(self.openai_batch_shape(self.router.batches_create(
            input_file_id=input_file_id,
            endpoint=endpoint,
            completion_window=completion_window,
            metadata=metadata,
            output_expires_after=output_expires_after,
        )))

    def handle_batches_list(self) -> None:
        payload = self.router.batches_list()
        self.write_json({
            "object": "list",
            "data": [self.openai_batch_shape(item) for item in payload.get("data", [])],
            "oauth_compat_route": payload.get("route"),
        })

    def handle_batches_retrieve(self, path: str) -> None:
        batch_id = self.path_part(path, 3)
        self.write_json(self.openai_batch_shape(self.router.batches_retrieve(batch_id)))

    def handle_batches_cancel(self, path: str) -> None:
        batch_id = self.path_part(path, 3)
        self.write_json(self.openai_batch_shape(self.router.batches_cancel(batch_id)))

    def handle_videos_create(self) -> None:
        self.write_json(self.router.videos_create(**self.video_create_kwargs("create")))

    def handle_videos_edits_create(self) -> None:
        self.write_json(self.router.videos_create(**self.video_create_kwargs("edit")))

    def handle_videos_extensions_create(self) -> None:
        self.write_json(self.router.videos_create(**self.video_create_kwargs("extension")))

    def handle_videos_remix(self, path: str) -> None:
        body = self.read_json()
        prompt = body.get("prompt") if isinstance(body.get("prompt"), str) else "Local video remix storyboard"
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        self.write_json(self.router.videos_remix(self.path_part(path, 3), prompt=prompt, metadata=metadata))

    def handle_videos_list(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        limit = self.int_query(query, "limit", 100)
        self.write_json(self.router.videos_list(limit=limit))

    def handle_videos_retrieve(self, path: str) -> None:
        self.write_json(self.router.videos_retrieve(self.path_part(path, 3)))

    def handle_videos_delete(self, path: str) -> None:
        self.write_json(self.router.videos_delete(self.path_part(path, 3)))

    def handle_videos_content(self, path: str) -> None:
        content, content_type = self.router.videos_content(self.path_part(path, 3))
        self.write_bytes(
            content,
            content_type=content_type,
            headers={"X-OAuth-Compat-Route": "local_video_storyboard_sandbox"},
        )

    def handle_video_characters_list(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        limit = self.int_query(query, "limit", 100)
        self.write_json(self.router.video_characters_list(limit=limit))

    def handle_video_characters_retrieve(self, path: str) -> None:
        self.write_json(self.router.video_characters_retrieve(self.path_part(path, 4)))

    def video_create_kwargs(self, operation: str) -> Dict[str, Any]:
        body, _file_item = self.read_json_or_multipart()
        prompt = (
            body.get("prompt")
            if isinstance(body.get("prompt"), str)
            else body.get("input")
            if isinstance(body.get("input"), str)
            else f"Local video {operation} storyboard"
        )
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        return {
            "prompt": prompt,
            "model": body.get("model") if isinstance(body.get("model"), str) else None,
            "size": body.get("size") if isinstance(body.get("size"), str) else None,
            "seconds": str(body.get("seconds")) if body.get("seconds") is not None else None,
            "quality": body.get("quality") if isinstance(body.get("quality"), str) else None,
            "operation": operation,
            "metadata": metadata,
        }

    def handle_fine_tuning_jobs_create(self) -> None:
        body = self.read_json()
        model = body.get("model")
        training_file = body.get("training_file")
        if not isinstance(model, str) or not model:
            raise ValueError("model must be a non-empty string")
        if not isinstance(training_file, str) or not training_file:
            raise ValueError("training_file must be a non-empty string")
        validation_file = body.get("validation_file") if isinstance(body.get("validation_file"), str) else None
        suffix = body.get("suffix") if isinstance(body.get("suffix"), str) else None
        hyperparameters = body.get("hyperparameters") if isinstance(body.get("hyperparameters"), dict) else None
        integrations = body.get("integrations") if isinstance(body.get("integrations"), list) else None
        seed = body.get("seed") if isinstance(body.get("seed"), int) else None
        method = body.get("method") if isinstance(body.get("method"), dict) else None
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        self.write_json(self.router.fine_tuning_jobs_create(
            model=model,
            training_file=training_file,
            validation_file=validation_file,
            suffix=suffix,
            hyperparameters=hyperparameters,
            integrations=integrations,
            seed=seed,
            method=method,
            metadata=metadata,
        ))

    def handle_fine_tuning_jobs_list(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        limit = self.int_query(query, "limit", 100)
        self.write_json(self.router.fine_tuning_jobs_list(limit=limit))

    def handle_fine_tuning_jobs_retrieve(self, path: str) -> None:
        self.write_json(self.router.fine_tuning_jobs_retrieve(self.path_part(path, 4)))

    def handle_fine_tuning_jobs_cancel(self, path: str) -> None:
        self.write_json(self.router.fine_tuning_jobs_cancel(self.path_part(path, 4)))

    def handle_fine_tuning_jobs_pause(self, path: str) -> None:
        self.write_json(self.router.fine_tuning_jobs_pause(self.path_part(path, 4)))

    def handle_fine_tuning_jobs_resume(self, path: str) -> None:
        self.write_json(self.router.fine_tuning_jobs_resume(self.path_part(path, 4)))

    def handle_fine_tuning_job_events_list(self, path: str) -> None:
        query = parse_qs(urlparse(self.path).query)
        limit = self.int_query(query, "limit", 100)
        self.write_json(self.router.fine_tuning_job_events_list(self.path_part(path, 4), limit=limit))

    def handle_fine_tuning_job_checkpoints_list(self, path: str) -> None:
        query = parse_qs(urlparse(self.path).query)
        limit = self.int_query(query, "limit", 100)
        self.write_json(self.router.fine_tuning_job_checkpoints_list(self.path_part(path, 4), limit=limit))

    def handle_fine_tuning_checkpoint_permissions_list(self, path: str) -> None:
        query = parse_qs(urlparse(self.path).query)
        limit = self.int_query(query, "limit", 100)
        self.write_json(self.router.fine_tuning_checkpoint_permissions_list(self.path_part(path, 4), limit=limit))

    def handle_fine_tuning_checkpoint_permissions_create(self, path: str) -> None:
        body = self.read_json()
        project_id = body.get("project_id")
        if not isinstance(project_id, str) or not project_id:
            raise ValueError("project_id must be a non-empty string")
        self.write_json(self.router.fine_tuning_checkpoint_permissions_create(
            self.path_part(path, 4),
            project_id=project_id,
        ))

    def handle_fine_tuning_checkpoint_permissions_delete(self, path: str) -> None:
        self.write_json(self.router.fine_tuning_checkpoint_permissions_delete(
            self.path_part(path, 4),
            self.path_part(path, 6),
        ))

    def handle_organization_sandbox(self, path: str, method: str) -> None:
        body: Dict[str, Any] | None = None
        if method.upper() == "POST":
            body = self.read_json()
        self.write_json(self.router.organization_sandbox(path, method=method, body=body))

    def handle_fine_tuning_grader_run(self) -> None:
        body = self.read_json()
        grader = body.get("grader")
        if not isinstance(grader, dict):
            raise ValueError("grader must be an object")
        if "model_sample" in body:
            model_sample = body.get("model_sample")
        elif "sample" in body:
            model_sample = body.get("sample")
        else:
            raise ValueError("model_sample must be provided")
        item = body.get("item") if isinstance(body.get("item"), dict) else {}
        self.write_json(self.router.fine_tuning_graders_run(grader, model_sample=model_sample, item=item))

    def handle_fine_tuning_grader_validate(self) -> None:
        body = self.read_json()
        grader = body.get("grader") if isinstance(body.get("grader"), dict) else body
        if not isinstance(grader, dict):
            raise ValueError("grader must be an object")
        self.write_json(self.router.fine_tuning_graders_validate(grader))

    def handle_evals_create(self) -> None:
        body = self.read_json()
        name = body.get("name") if isinstance(body.get("name"), str) else "oauth-local-eval"
        data_source_config = body.get("data_source_config") if isinstance(body.get("data_source_config"), dict) else {"type": "custom", "item_schema": {}}
        criteria = body.get("testing_criteria") if isinstance(body.get("testing_criteria"), list) else []
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        self.write_json(self.router.evals_create(
            name=name,
            data_source_config=data_source_config,
            testing_criteria=criteria,
            metadata=metadata,
        ))

    def handle_evals_list(self) -> None:
        payload = self.router.evals_list()
        self.write_json({
            "object": "list",
            "data": payload.get("data", []),
            "oauth_compat_route": payload.get("route"),
        })

    def handle_evals_retrieve(self, path: str) -> None:
        eval_id = self.path_part(path, 3)
        self.write_json(self.router.evals_retrieve(eval_id))

    def handle_evals_update(self, path: str) -> None:
        eval_id = self.path_part(path, 3)
        body = self.read_json()
        name = body.get("name") if isinstance(body.get("name"), str) else None
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        self.write_json(self.router.evals_update(eval_id, name=name, metadata=metadata))

    def handle_evals_delete(self, path: str) -> None:
        eval_id = self.path_part(path, 3)
        self.write_json(self.router.evals_delete(eval_id))

    def handle_eval_runs_create(self, path: str) -> None:
        eval_id = self.path_part(path, 3)
        body = self.read_json()
        name = body.get("name") if isinstance(body.get("name"), str) else "oauth-local-eval-run"
        data_source = body.get("data_source") if isinstance(body.get("data_source"), dict) else {"type": "jsonl", "source": {"type": "file_content", "content": []}}
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        self.write_json(self.router.eval_runs_create(eval_id, name=name, data_source=data_source, metadata=metadata))

    def handle_eval_runs_list(self, path: str) -> None:
        eval_id = self.path_part(path, 3)
        payload = self.router.eval_runs_list(eval_id)
        self.write_json({
            "object": "list",
            "data": payload.get("data", []),
            "oauth_compat_route": payload.get("route"),
        })

    def handle_eval_runs_retrieve(self, path: str) -> None:
        eval_id = self.path_part(path, 3)
        run_id = self.path_part(path, 5)
        self.write_json(self.router.eval_runs_retrieve(eval_id, run_id))

    def handle_eval_runs_cancel(self, path: str) -> None:
        eval_id = self.path_part(path, 3)
        run_id = self.path_part(path, 5)
        self.write_json(self.router.eval_runs_cancel(eval_id, run_id))

    def handle_eval_runs_delete(self, path: str) -> None:
        eval_id = self.path_part(path, 3)
        run_id = self.path_part(path, 5)
        self.write_json(self.router.eval_runs_delete(eval_id, run_id))

    def handle_eval_output_items_list(self, path: str) -> None:
        eval_id = self.path_part(path, 3)
        run_id = self.path_part(path, 5)
        payload = self.router.eval_output_items_list(eval_id, run_id)
        self.write_json({
            "object": "list",
            "data": payload.get("data", []),
            "oauth_compat_route": payload.get("route"),
        })

    def handle_eval_output_items_retrieve(self, path: str) -> None:
        eval_id = self.path_part(path, 3)
        run_id = self.path_part(path, 5)
        output_item_id = self.path_part(path, 7)
        self.write_json(self.router.eval_output_items_retrieve(eval_id, run_id, output_item_id))

    def handle_vector_stores_create(self) -> None:
        body = self.read_json()
        name = body.get("name") if isinstance(body.get("name"), str) else "oauth-local-vector-store"
        self.write_json(self.openai_vector_store_shape(self.router.vector_stores_create(name=name)))

    def handle_vector_stores_list(self) -> None:
        payload = self.router.vector_stores_list()
        self.write_json({
            "object": "list",
            "data": [self.openai_vector_store_shape(item) for item in payload.get("data", [])],
            "oauth_compat_route": payload.get("route"),
        })

    def handle_vector_stores_retrieve(self, path: str) -> None:
        store_id = self.path_part(path, 3)
        self.write_json(self.openai_vector_store_shape(self.router.vector_stores_retrieve(store_id)))

    def handle_vector_stores_delete(self, path: str) -> None:
        store_id = self.path_part(path, 3)
        self.write_json(self.router.vector_stores_delete(store_id))

    def handle_vector_store_files_create(self, path: str) -> None:
        store_id = self.path_part(path, 3)
        body = self.read_json()
        file_id = body.get("file_id")
        if not isinstance(file_id, str) or not file_id:
            raise ValueError("file_id must be a non-empty string")
        attributes = body.get("attributes") if isinstance(body.get("attributes"), dict) else None
        self.write_json(self.openai_vector_store_file_shape(
            self.router.vector_store_files_create(store_id, file_id, attributes=attributes)
        ))

    def handle_vector_store_files_list(self, path: str) -> None:
        store_id = self.path_part(path, 3)
        payload = self.router.vector_store_files_list(store_id)
        self.write_json({
            "object": "list",
            "data": [self.openai_vector_store_file_shape(item) for item in payload.get("data", [])],
            "oauth_compat_route": payload.get("route"),
        })

    def handle_vector_store_files_retrieve(self, path: str) -> None:
        store_id = self.path_part(path, 3)
        file_id = self.path_part(path, 5)
        self.write_json(self.openai_vector_store_file_shape(self.router.vector_store_files_retrieve(store_id, file_id)))

    def handle_vector_store_files_content(self, path: str) -> None:
        store_id = self.path_part(path, 3)
        file_id = self.path_part(path, 5)
        self.write_json(self.router.vector_store_files_content(store_id, file_id))

    def handle_vector_store_files_delete(self, path: str) -> None:
        store_id = self.path_part(path, 3)
        file_id = self.path_part(path, 5)
        self.write_json(self.router.vector_store_files_delete(store_id, file_id))

    def handle_vector_store_file_batches_create(self, path: str) -> None:
        store_id = self.path_part(path, 3)
        body = self.read_json()
        file_ids = body.get("file_ids")
        if not isinstance(file_ids, list):
            raise ValueError("file_ids must be a list")
        attributes = body.get("attributes") if isinstance(body.get("attributes"), dict) else None
        self.write_json(self.openai_vector_store_file_batch_shape(
            self.router.vector_store_file_batches_create(store_id, file_ids, attributes=attributes)
        ))

    def handle_vector_store_file_batches_retrieve(self, path: str) -> None:
        store_id = self.path_part(path, 3)
        batch_id = self.path_part(path, 5)
        self.write_json(self.openai_vector_store_file_batch_shape(
            self.router.vector_store_file_batches_retrieve(store_id, batch_id)
        ))

    def handle_vector_store_file_batches_cancel(self, path: str) -> None:
        store_id = self.path_part(path, 3)
        batch_id = self.path_part(path, 5)
        self.write_json(self.openai_vector_store_file_batch_shape(
            self.router.vector_store_file_batches_cancel(store_id, batch_id)
        ))

    def handle_vector_store_file_batches_files_list(self, path: str) -> None:
        store_id = self.path_part(path, 3)
        batch_id = self.path_part(path, 5)
        payload = self.router.vector_store_file_batches_files_list(store_id, batch_id)
        self.write_json({
            "object": "list",
            "data": [self.openai_vector_store_file_shape(item) for item in payload.get("data", [])],
            "oauth_compat_route": payload.get("route"),
        })

    def handle_vector_stores_add_text(self, path: str) -> None:
        store_id = path.split("/")[3]
        body = self.read_json()
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
        self.write_json(self.router.vector_stores_add_text(store_id, text, metadata=metadata))

    def handle_vector_stores_search(self, path: str) -> None:
        store_id = path.split("/")[3]
        body = self.read_json()
        query = body.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        limit = body.get("limit", 5)
        if not isinstance(limit, int):
            limit = 5
        self.write_json(self.router.vector_stores_search(store_id, query, limit=limit))

    def handle_local_eval_text_expectation(self) -> None:
        body = self.read_json()
        prompt = body.get("prompt")
        expected = body.get("expected_substring")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if not isinstance(expected, str) or not expected:
            raise ValueError("expected_substring must be a non-empty string")
        self.write_json(self.router.eval_text_expectation(prompt, expected))

    def capabilities_payload(self) -> Dict[str, Any]:
        return {
            "object": "oauth_compat.capabilities",
            "direct_official_oauth": [
                "/v1/audio/transcriptions",
                "/v1/embeddings",
                "/v1/realtime/client_secrets",
                "/v1/realtime/translations/client_secrets",
                "/v1/realtime/calls",
            ],
            "local_openai_compatible_proxy": [
                "OPTIONS /v1/*",
                "/v1/oauth-readiness",
                "/v1/oauth-compatibility-guide",
                "/v1/oauth-client-config",
                "/v1/oauth-quickstart",
                "/v1/oauth-coverage-map",
                "/v1/oauth-route-policy",
                "/v1/oauth-boundary-playbook",
                "/v1/oauth-status",
                "/v1/oauth-goal-audit",
                "/v1/oauth-classify",
                "/v1/organization/*",
                "/v1/projects/{project_id}/*",
                "/v1/videos",
                "/v1/videos/{video_id}",
                "/v1/videos/{video_id}/content",
                "/v1/videos/{video_id}/remix",
                "/v1/videos/characters",
                "/v1/videos/characters/{character_id}",
                "/v1/videos/edits",
                "/v1/videos/extensions",
                "/v1/models",
                "/v1/models/{model}",
                "/v1/skills",
                "/v1/skills/{skill_id}",
                "/v1/skills/{skill_id}/content",
                "/v1/skills/{skill_id}/versions",
                "/v1/skills/{skill_id}/versions/{version}",
                "/v1/skills/{skill_id}/versions/{version}/content",
                "/v1/containers",
                "/v1/containers/{container_id}",
                "/v1/containers/{container_id}/files",
                "/v1/containers/{container_id}/files/{file_id}",
                "/v1/containers/{container_id}/files/{file_id}/content",
                "/v1/chatkit/sessions",
                "/v1/chatkit/sessions/{session_id}/cancel",
                "/v1/chatkit/threads",
                "/v1/chatkit/threads/{thread_id}",
                "/v1/chatkit/threads/{thread_id}/items",
                "/v1/conversations",
                "/v1/conversations/{conversation_id}",
                "/v1/conversations/{conversation_id}/items",
                "/v1/conversations/{conversation_id}/items/{item_id}",
                "/v1/assistants",
                "/v1/assistants/{assistant_id}",
                "/v1/threads",
                "/v1/threads/{thread_id}",
                "/v1/threads/{thread_id}/messages",
                "/v1/threads/{thread_id}/messages/{message_id}",
                "/v1/threads/{thread_id}/runs",
                "/v1/threads/{thread_id}/runs/{run_id}",
                "/v1/threads/{thread_id}/runs/{run_id}/cancel",
                "/v1/threads/{thread_id}/runs/{run_id}/submit_tool_outputs",
                "/v1/threads/{thread_id}/runs/{run_id}/steps",
                "/v1/threads/{thread_id}/runs/{run_id}/steps/{step_id}",
                "/v1/threads/runs",
                "/v1/completions",
                "/v1/responses",
                "/v1/responses/compact",
                "/v1/responses/input_tokens",
                "/v1/chat/completions",
                "/v1/chat/completions/{completion_id}",
                "/v1/chat/completions/{completion_id}/messages",
                "/v1/embeddings",
                "/v1/images/generations",
                "/v1/images/edits",
                "/v1/images/variations",
                "/v1/moderations",
                "/v1/audio/speech",
                "/v1/audio/transcriptions",
                "/v1/audio/translations",
                "/v1/audio/voices",
                "/v1/audio/voice_consents",
                "/v1/audio/voice_consents/{consent_id}",
                "/v1/realtime/sessions",
                "/v1/realtime/transcription_sessions",
                "/v1/realtime/calls/{call_id}/accept",
                "/v1/realtime/calls/{call_id}/hangup",
                "/v1/realtime/calls/{call_id}/refer",
                "/v1/realtime/calls/{call_id}/reject",
                "/v1/files",
                "/v1/files/{file_id}",
                "/v1/files/{file_id}/content",
                "/v1/uploads",
                "/v1/uploads/{upload_id}/parts",
                "/v1/uploads/{upload_id}/complete",
                "/v1/uploads/{upload_id}/cancel",
                "/v1/batches",
                "/v1/batches/{batch_id}",
                "/v1/batches/{batch_id}/cancel",
                "/v1/fine_tuning/jobs",
                "/v1/fine_tuning/jobs/{fine_tuning_job_id}",
                "/v1/fine_tuning/jobs/{fine_tuning_job_id}/cancel",
                "/v1/fine_tuning/jobs/{fine_tuning_job_id}/checkpoints",
                "/v1/fine_tuning/jobs/{fine_tuning_job_id}/events",
                "/v1/fine_tuning/jobs/{fine_tuning_job_id}/pause",
                "/v1/fine_tuning/jobs/{fine_tuning_job_id}/resume",
                "/v1/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions",
                "/v1/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions/{permission_id}",
                "/v1/fine_tuning/alpha/graders/run",
                "/v1/fine_tuning/alpha/graders/validate",
                "/v1/responses/{response_id}",
                "/v1/responses/{response_id}/cancel",
                "/v1/responses/{response_id}/input_items",
                "/v1/evals",
                "/v1/evals/{eval_id}",
                "/v1/evals/{eval_id}/runs",
                "/v1/evals/{eval_id}/runs/{run_id}",
                "/v1/evals/{eval_id}/runs/{run_id}/output_items",
                "/v1/evals/{eval_id}/runs/{run_id}/output_items/{output_item_id}",
                "/v1/vector_stores",
                "/v1/vector_stores/{vector_store_id}",
                "/v1/vector_stores/{vector_store_id}/file_batches",
                "/v1/vector_stores/{vector_store_id}/file_batches/{batch_id}",
                "/v1/vector_stores/{vector_store_id}/file_batches/{batch_id}/cancel",
                "/v1/vector_stores/{vector_store_id}/file_batches/{batch_id}/files",
                "/v1/vector_stores/{vector_store_id}/files",
                "/v1/vector_stores/{vector_store_id}/files/{file_id}",
                "/v1/vector_stores/{vector_store_id}/files/{file_id}/content",
            ],
            "local_extension_routes": [
                "/v1/vector_stores/{vector_store_id}/items",
                "/v1/vector_stores/{vector_store_id}/search",
                "/v1/local/evals/text_expectation",
            ],
            "local_or_chatgpt_backend_compat": [
                "Codex text and vision",
                "Codex image_generation tool",
                "Local image edits and variations through Codex vision plus image generation",
                "Realtime audio PCM16 speech substitute",
                "Realtime session compatibility aliases through OAuth Realtime client secrets",
                "Local audio translation through OAuth transcription plus Codex text translation",
                "ChatGPT backend file upload",
                "Local Upload sessions plus ChatGPT backend file completion",
                "Local Batch processing over local proxy routes",
                "Local fine-tuning job lifecycle, checkpoints, events, and checkpoint permission metadata",
                "Local fine-tuning grader run/validate for string_check and multi graders",
                "Local heuristic moderation",
                "Local stored Responses lifecycle",
                "Local stored Chat Completions lifecycle",
                "Local Assistants and Threads orchestration plus Codex text",
                "Local vector stores plus OAuth embeddings",
                "Local eval helper plus Codex text",
                "Local container metadata and file storage",
                "Local ChatKit sessions, threads, and items",
                "Local Skills registry over installed Codex skills and local skill bundles",
                "Local Conversations and conversation items",
                "Local Organization, Project, Usage, and Cost sandbox metadata",
                "Local video storyboard/job metadata and content manifests",
            ],
            "browser_support": {
                "cors": "All local proxy responses include CORS headers; browser preflight OPTIONS returns 204.",
            },
            "known_boundary_responses": {
                "enabled": True,
                "description": (
                    "Known official OpenAI paths that this local proxy cannot handle return a structured "
                    "oauth_compat.boundary JSON error instead of a generic 404."
                ),
            },
            "platform_fallback": global_fallback_state(),
            "model_discovery": {
                "discovered_count": len(self.router.oauth.discovered_model_ids),
                "models": self.router.oauth.model_ids,
                "error": self.router.oauth.model_probe_error,
            },
            "hard_boundaries": [
                "Most OpenAI Platform resources still require API keys or Admin API keys.",
                "The bridge records blocked routes instead of bypassing authorization.",
            ],
        }

    def readiness_payload(self) -> Dict[str, Any]:
        payload = build_readiness_report()
        payload["object"] = "oauth_compat.readiness"
        return payload

    def compatibility_guide_payload(self) -> Dict[str, Any]:
        payload = build_compatibility_guide_report()
        payload["object"] = "oauth_compat.compatibility_guide"
        return payload

    def client_config_payload(self) -> Dict[str, Any]:
        host = self.headers.get("Host", "127.0.0.1:8787")
        proto = self.headers.get("X-Forwarded-Proto", "http")
        payload = build_client_config_report(base_url=f"{proto}://{host}/v1")
        payload["object"] = "oauth_compat.client_config"
        return payload

    def quickstart_payload(self) -> Dict[str, Any]:
        host = self.headers.get("Host", "127.0.0.1:8787")
        proto = self.headers.get("X-Forwarded-Proto", "http")
        host_name, _, port_value = host.partition(":")
        try:
            port = int(port_value) if port_value else 8787
        except ValueError:
            port = 8787
        payload = build_quickstart_report(
            host=host_name or "127.0.0.1",
            port=port,
            base_url=f"{proto}://{host}/v1",
        )
        payload["object"] = "oauth_compat.quickstart"
        return payload

    def coverage_map_payload(self) -> Dict[str, Any]:
        payload = build_coverage_map_report()
        payload["object"] = "oauth_compat.coverage_map"
        return payload

    def route_policy_payload(self) -> Dict[str, Any]:
        payload = build_route_policy_report()
        payload["object"] = "oauth_compat.route_policy"
        return payload

    def boundary_playbook_payload(self) -> Dict[str, Any]:
        payload = build_boundary_playbook_report()
        payload["object"] = "oauth_compat.boundary_playbook"
        return payload

    def status_payload(self) -> Dict[str, Any]:
        host = self.headers.get("Host", "127.0.0.1:8787")
        proto = self.headers.get("X-Forwarded-Proto", "http")
        host_name, _, port_value = host.partition(":")
        try:
            port = int(port_value) if port_value else 8787
        except ValueError:
            port = 8787
        payload = build_status_report(
            host=host_name or "127.0.0.1",
            port=port,
            timeout_seconds=0.1,
            refresh_env=False,
            write_dependencies=False,
        )
        payload["base_url"] = f"{proto}://{host}/v1"
        payload["object"] = "oauth_compat.status"
        return payload

    def goal_audit_payload(self) -> Dict[str, Any]:
        payload = build_goal_audit_report()
        payload["object"] = "oauth_compat.goal_audit"
        return payload

    def classify_payload(self) -> Dict[str, Any]:
        query = parse_qs(urlparse(self.path).query)
        values = query.get("path") or query.get("url")
        if not values or not values[0].strip():
            return {
                "object": "oauth_compat.path_classification",
                "ok": False,
                "error": {
                    "message": "Missing required query parameter: path",
                    "type": "invalid_request_error",
                },
            }
        payload = classify_openai_path(values[0])
        payload["object"] = "oauth_compat.path_classification"
        return payload

    def write_known_boundary_or_not_found(self, path: str, method: str) -> None:
        payload, status = known_boundary_payload(path, method)
        fallback = payload.get("platform_fallback") if isinstance(payload.get("platform_fallback"), dict) else {}
        if fallback.get("can_forward") is True:
            self.forward_platform_request(path, method)
            return
        self.write_json(payload, status)

    def maybe_forward_preferred_platform(self, path: str, method: str) -> bool:
        if not path.startswith("/v1/") or path.startswith("/v1/oauth-") or path.startswith("/v1/local/"):
            return False
        prefer_header = truthy(self.headers.get("X-OAuth-Compat-Prefer-Platform"))
        classified = classify_openai_path(path)
        if not classified.get("ok"):
            return False
        match = classified.get("match") if isinstance(classified.get("match"), dict) else {}
        category = str(match.get("category") or "not_probed_directly")
        fallback = path_fallback_state(path, category=category, prefer_platform=prefer_header)
        if fallback.get("can_forward") is True and fallback.get("prefer_platform") is True:
            self.forward_platform_request(path, method)
            return True
        return False

    def forward_platform_request(self, path: str, method: str) -> None:
        token, credential_env = credential_for_path(path)
        if not token:
            payload, status = known_boundary_payload(path, method)
            self.write_json(payload, status)
            return

        query = urlparse(self.path).query
        target_url = f"{platform_base_url()}{path[3:]}"
        if query:
            target_url = f"{target_url}?{query}"
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else None
        headers: Dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "chatgpt-oauth-bridge-platform-fallback/0.1",
        }
        for name in (
            "Content-Type",
            "Accept",
            "OpenAI-Organization",
            "OpenAI-Project",
            "OpenAI-Beta",
            "Idempotency-Key",
        ):
            value = self.headers.get(name)
            if value:
                headers[name] = value
        try:
            with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
                response = client.request(method, target_url, content=body, headers=headers)
        except Exception as exc:
            self.write_json({
                "error": {
                    "message": f"Platform fallback request failed: {type(exc).__name__}: {str(exc)[:300]}",
                    "type": "platform_fallback_error",
                },
                "object": "oauth_compat.platform_fallback_error",
                "method": method,
                "path": path,
                "platform_base_url": platform_base_url(),
                "credential_env": credential_env,
            }, HTTPStatus.BAD_GATEWAY)
            return
        self.write_raw_response(
            response.status_code,
            response.content,
            content_type=response.headers.get("content-type", "application/octet-stream"),
            headers={
                "X-OAuth-Compat-Route": "platform_fallback",
                "X-OAuth-Platform-Credential": credential_env,
            },
        )

    def request_path(self) -> str:
        return urlparse(self.path).path

    def path_parts(self, path: str) -> list[str]:
        return [part for part in path.split("/") if part]

    def path_part(self, path: str, index: int) -> str:
        parts = path.split("/")
        if len(parts) <= index or not parts[index]:
            raise ValueError("missing path id")
        return unquote(parts[index])

    def input_to_text(self, input_value: Any) -> str:
        if isinstance(input_value, str):
            return input_value
        if isinstance(input_value, list):
            chunks = []
            for item in input_value:
                if isinstance(item, str):
                    chunks.append(item)
                elif isinstance(item, dict):
                    role = item.get("role")
                    content = item.get("content")
                    text_parts = []
                    if isinstance(content, str):
                        text_parts.append(content)
                    elif isinstance(content, list):
                        for content_item in content:
                            if isinstance(content_item, dict):
                                text = content_item.get("text") or content_item.get("input_text")
                                if isinstance(text, str):
                                    text_parts.append(text)
                    prefix = f"{role}: " if isinstance(role, str) else ""
                    if text_parts:
                        chunks.append(prefix + "\n".join(text_parts))
            return "\n".join(chunks)
        return str(input_value)

    def read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def read_json_or_multipart(self) -> tuple[Dict[str, Any], Dict[str, Any] | None]:
        content_type = self.headers.get("Content-Type", "")
        if content_type.startswith("multipart/form-data"):
            fields, files = self.read_multipart_form()
            body: Dict[str, Any] = dict(fields)
            for key in ("metadata",):
                value = body.get(key)
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                    except json.JSONDecodeError:
                        parsed = None
                    if isinstance(parsed, dict):
                        body[key] = parsed
            file_item = files.get("file") or files.get("content") or next(iter(files.values()), None)
            return body, file_item
        return self.read_json(), None

    def object_field(self, payload: Dict[str, Any], key: str) -> Dict[str, Any] | None:
        value = payload.get(key)
        return value if isinstance(value, dict) else None

    def int_query(self, query: Dict[str, list[str]], key: str, default: int) -> int:
        raw = query.get(key, [str(default)])[0]
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default

    def read_multipart_form(self) -> tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            raise ValueError("Content-Type must be multipart/form-data")
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length)
        header = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
        message = BytesParser(policy=email_default_policy).parsebytes(header + raw)
        fields: Dict[str, str] = {}
        files: Dict[str, Dict[str, Any]] = {}
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not isinstance(name, str) or not name:
                continue
            data = part.get_payload(decode=True) or b""
            filename = part.get_filename()
            if filename:
                files[name] = {
                    "filename": filename,
                    "content_type": part.get_content_type(),
                    "data": data,
                }
            else:
                fields[name] = data.decode("utf-8", errors="replace")
        return fields, files

    def write_uploaded_file(self, item: Dict[str, Any]) -> Path:
        ARTIFACTS.mkdir(exist_ok=True)
        filename = str(item.get("filename") or "upload.bin")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name) or "upload.bin"
        path = ARTIFACTS / f"compat_upload_{uuid.uuid4().hex}_{safe_name}"
        data = item.get("data")
        if not isinstance(data, bytes):
            raise ValueError("uploaded file data missing")
        path.write_bytes(data)
        return path

    def openai_file_shape(self, item: Dict[str, Any]) -> Dict[str, Any]:
        local_content_path = item.get("local_content_path")
        return {
            "id": item.get("id"),
            "object": "file",
            "bytes": item.get("bytes"),
            "created_at": item.get("created_at"),
            "filename": item.get("filename"),
            "purpose": item.get("purpose"),
            "status": item.get("status", "processed"),
            "oauth_compat_route": item.get("route"),
            "uri": item.get("uri"),
            "download_url_present": item.get("download_url_present"),
            "download_url_host": item.get("download_url_host"),
            "local_metadata_path": item.get("local_metadata_path"),
            "local_content_present": Path(local_content_path).exists() if isinstance(local_content_path, str) else False,
        }

    def openai_container_shape(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id"),
            "object": "container",
            "created_at": item.get("created_at"),
            "name": item.get("name"),
            "status": item.get("status"),
            "metadata": item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
            "expires_after": item.get("expires_after"),
            "oauth_compat_route": item.get("route"),
            "local_path": item.get("local_path"),
        }

    def openai_container_file_shape(self, item: Dict[str, Any]) -> Dict[str, Any]:
        local_content_path = item.get("local_content_path")
        return {
            "id": item.get("id"),
            "object": "container.file",
            "container_id": item.get("container_id"),
            "created_at": item.get("created_at"),
            "filename": item.get("filename"),
            "bytes": item.get("bytes"),
            "mime_type": item.get("mime_type"),
            "oauth_compat_route": item.get("route"),
            "local_content_present": Path(local_content_path).exists() if isinstance(local_content_path, str) else False,
        }

    def openai_upload_shape(self, item: Dict[str, Any]) -> Dict[str, Any]:
        file_item = item.get("file")
        return {
            "id": item.get("id"),
            "object": "upload",
            "bytes": item.get("bytes"),
            "created_at": item.get("created_at"),
            "expires_at": item.get("expires_at"),
            "filename": item.get("filename"),
            "purpose": item.get("purpose"),
            "status": item.get("status"),
            "file": self.openai_file_shape(file_item) if isinstance(file_item, dict) else None,
            "oauth_compat_route": item.get("route"),
            "mime_type": item.get("mime_type"),
            "part_count": item.get("part_count"),
        }

    def openai_upload_part_shape(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id"),
            "created_at": item.get("created_at"),
            "object": "upload.part",
            "upload_id": item.get("upload_id"),
            "oauth_compat_route": item.get("route"),
            "bytes": item.get("bytes"),
        }

    def openai_batch_shape(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id"),
            "object": "batch",
            "endpoint": item.get("endpoint"),
            "input_file_id": item.get("input_file_id"),
            "completion_window": item.get("completion_window"),
            "status": item.get("status"),
            "created_at": item.get("created_at"),
            "in_progress_at": item.get("in_progress_at"),
            "finalizing_at": item.get("finalizing_at"),
            "completed_at": item.get("completed_at"),
            "expires_at": item.get("expires_at"),
            "cancelling_at": item.get("cancelling_at"),
            "cancelled_at": item.get("cancelled_at"),
            "failed_at": item.get("failed_at"),
            "expired_at": item.get("expired_at"),
            "output_file_id": item.get("output_file_id"),
            "error_file_id": item.get("error_file_id"),
            "errors": item.get("errors"),
            "metadata": item.get("metadata"),
            "request_counts": item.get("request_counts"),
            "oauth_compat_route": item.get("route"),
        }

    def response_input_item_shape(self, input_value: Any, prompt: str) -> Dict[str, Any]:
        content: list[Dict[str, Any]]
        if isinstance(input_value, list):
            content = []
            for item in input_value:
                if isinstance(item, dict):
                    item_text = item.get("text") or item.get("input_text") or item.get("content")
                    if isinstance(item_text, str):
                        content.append({"type": "input_text", "text": item_text})
                elif isinstance(item, str):
                    content.append({"type": "input_text", "text": item})
            if not content:
                content = [{"type": "input_text", "text": prompt}]
        else:
            content = [{"type": "input_text", "text": prompt}]
        return {
            "id": f"msg_{uuid.uuid4().hex}",
            "type": "message",
            "role": "user",
            "content": content,
        }

    def openai_vector_store_shape(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item_count = int(item.get("item_count", 0) or 0)
        return {
            "id": item.get("id"),
            "object": "vector_store",
            "created_at": item.get("created_at"),
            "name": item.get("name"),
            "usage_bytes": 0,
            "file_counts": {
                "in_progress": 0,
                "completed": item_count,
                "failed": 0,
                "cancelled": 0,
                "total": item_count,
            },
            "metadata": {"local_item_count": item_count},
            "oauth_compat_route": item.get("route"),
        }

    def model_shape(self, model_id: str, *, created: int | None = None) -> Dict[str, Any]:
        return {
            "id": model_id,
            "object": "model",
            "created": created or int(time.time()),
            "owned_by": "chatgpt-codex-oauth",
            "oauth_compat_route": "codex_models",
        }

    def openai_vector_store_file_shape(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id"),
            "object": "vector_store.file",
            "created_at": item.get("created_at"),
            "vector_store_id": item.get("vector_store_id"),
            "status": item.get("status", "completed"),
            "usage_bytes": item.get("usage_bytes", 0),
            "attributes": item.get("attributes", {}),
            "metadata": item.get("metadata", {}),
            "oauth_compat_route": item.get("route"),
        }

    def openai_vector_store_file_batch_shape(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id"),
            "object": "vector_store.file_batch",
            "created_at": item.get("created_at"),
            "vector_store_id": item.get("vector_store_id"),
            "status": item.get("status", "completed"),
            "file_counts": item.get("file_counts", {}),
            "oauth_compat_route": item.get("route"),
        }

    def write_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def write_empty(self, status: HTTPStatus) -> None:
        self.send_response(status.value)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def write_chat_stream(self, payload: Dict[str, Any]) -> None:
        chat_id = str(payload["id"])
        created = int(payload["created"])
        model = str(payload.get("model") or "")
        content = str(payload["choices"][0]["message"].get("content") or "")
        self.start_sse()
        self.write_sse_data({
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        })
        if content:
            self.write_sse_data({
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
            })
        self.write_sse_data({
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        })
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def write_completion_stream(self, payload: Dict[str, Any]) -> None:
        completion_id = str(payload["id"])
        created = int(payload["created"])
        model = str(payload.get("model") or "")
        text = str(payload["choices"][0].get("text") or "")
        self.start_sse()
        if text:
            self.write_sse_data({
                "id": completion_id,
                "object": "text_completion",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "text": text, "logprobs": None, "finish_reason": None}],
            })
        self.write_sse_data({
            "id": completion_id,
            "object": "text_completion",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "text": "", "logprobs": None, "finish_reason": "stop"}],
        })
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def write_response_stream(self, payload: Dict[str, Any]) -> None:
        response_id = str(payload["id"])
        model = str(payload.get("model") or "")
        created_at = float(payload.get("created_at") or time.time())
        text = str(payload.get("output_text") or "")
        message_id = str(payload["output"][0]["id"])
        response_base = {
            "id": response_id,
            "object": "response",
            "created_at": created_at,
            "model": model,
            "output": [],
            "parallel_tool_calls": False,
            "tool_choice": "auto",
            "tools": [],
            "status": "in_progress",
        }
        output_item = {
            "id": message_id,
            "type": "message",
            "role": "assistant",
            "status": "in_progress",
            "content": [],
        }
        final_item = {
            **output_item,
            "status": "completed",
            "content": [{"type": "output_text", "text": text, "annotations": []}],
        }
        final_response = {**response_base, "status": "completed", "output": [final_item]}

        self.start_sse()
        self.write_sse_event("response.created", {"type": "response.created", "sequence_number": 0, "response": response_base})
        self.write_sse_event("response.output_item.added", {
            "type": "response.output_item.added",
            "sequence_number": 1,
            "output_index": 0,
            "item": output_item,
        })
        self.write_sse_event("response.content_part.added", {
            "type": "response.content_part.added",
            "sequence_number": 2,
            "output_index": 0,
            "content_index": 0,
            "item_id": message_id,
            "part": {"type": "output_text", "text": "", "annotations": []},
        })
        if text:
            self.write_sse_event("response.output_text.delta", {
                "type": "response.output_text.delta",
                "sequence_number": 3,
                "output_index": 0,
                "content_index": 0,
                "item_id": message_id,
                "delta": text,
                "logprobs": [],
            })
        self.write_sse_event("response.output_text.done", {
            "type": "response.output_text.done",
            "sequence_number": 4,
            "output_index": 0,
            "content_index": 0,
            "item_id": message_id,
            "text": text,
            "logprobs": [],
        })
        self.write_sse_event("response.content_part.done", {
            "type": "response.content_part.done",
            "sequence_number": 5,
            "output_index": 0,
            "content_index": 0,
            "item_id": message_id,
            "part": {"type": "output_text", "text": text, "annotations": []},
        })
        self.write_sse_event("response.output_item.done", {
            "type": "response.output_item.done",
            "sequence_number": 6,
            "output_index": 0,
            "item": final_item,
        })
        self.write_sse_event("response.completed", {
            "type": "response.completed",
            "sequence_number": 7,
            "response": final_response,
        })
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def start_sse(self) -> None:
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

    def write_sse_data(self, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.wfile.write(b"data: " + data + b"\n\n")
        self.wfile.flush()

    def write_sse_event(self, event: str, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.wfile.write(f"event: {event}\n".encode("utf-8"))
        self.wfile.write(b"data: " + data + b"\n\n")
        self.wfile.flush()

    def write_bytes(self, data: bytes, *, content_type: str, headers: Dict[str, str] | None = None) -> None:
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def write_raw_response(
        self,
        status_code: int,
        data: bytes,
        *,
        content_type: str,
        headers: Dict[str, str] | None = None,
    ) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)


def make_server(host: str, port: int) -> ThreadingHTTPServer:
    CompatHandler.router = OAuthFeatureRouter()
    return ThreadingHTTPServer((host, port), CompatHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local OpenAI-compatible OAuth-only proxy.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    server = make_server(args.host, args.port)
    print(json.dumps({
        "host": args.host,
        "port": server.server_address[1],
        "base_url": f"http://{args.host}:{server.server_address[1]}/v1",
        "routes": [
            "OPTIONS /v1/*",
            "/v1/oauth-readiness",
            "/v1/oauth-compatibility-guide",
            "/v1/oauth-client-config",
            "/v1/oauth-quickstart",
            "/v1/oauth-coverage-map",
            "/v1/oauth-route-policy",
            "/v1/oauth-boundary-playbook",
            "/v1/oauth-status",
            "/v1/oauth-goal-audit",
            "/v1/oauth-classify",
            "/v1/organization/*",
            "/v1/projects/{project_id}/*",
            "/v1/videos",
            "/v1/videos/{video_id}",
            "/v1/videos/{video_id}/content",
            "/v1/videos/{video_id}/remix",
            "/v1/videos/characters",
            "/v1/videos/characters/{character_id}",
            "/v1/videos/edits",
            "/v1/videos/extensions",
            "/v1/responses",
            "/v1/responses/compact",
            "/v1/responses/input_tokens",
            "/v1/skills",
            "/v1/skills/{skill_id}",
            "/v1/skills/{skill_id}/content",
            "/v1/skills/{skill_id}/versions",
            "/v1/skills/{skill_id}/versions/{version}",
            "/v1/skills/{skill_id}/versions/{version}/content",
            "/v1/containers",
            "/v1/containers/{container_id}",
            "/v1/containers/{container_id}/files",
            "/v1/containers/{container_id}/files/{file_id}",
            "/v1/containers/{container_id}/files/{file_id}/content",
            "/v1/chatkit/sessions",
            "/v1/chatkit/sessions/{session_id}/cancel",
            "/v1/chatkit/threads",
            "/v1/chatkit/threads/{thread_id}",
            "/v1/chatkit/threads/{thread_id}/items",
            "/v1/conversations",
            "/v1/conversations/{conversation_id}",
            "/v1/conversations/{conversation_id}/items",
            "/v1/conversations/{conversation_id}/items/{item_id}",
            "/v1/responses/{response_id}",
            "/v1/responses/{response_id}/cancel",
            "/v1/responses/{response_id}/input_items",
            "/v1/assistants",
            "/v1/assistants/{assistant_id}",
            "/v1/threads",
            "/v1/threads/{thread_id}",
            "/v1/threads/{thread_id}/messages",
            "/v1/threads/{thread_id}/messages/{message_id}",
            "/v1/threads/{thread_id}/runs",
            "/v1/threads/{thread_id}/runs/{run_id}",
            "/v1/threads/{thread_id}/runs/{run_id}/cancel",
            "/v1/threads/{thread_id}/runs/{run_id}/submit_tool_outputs",
            "/v1/threads/{thread_id}/runs/{run_id}/steps",
            "/v1/threads/{thread_id}/runs/{run_id}/steps/{step_id}",
            "/v1/threads/runs",
            "/v1/completions",
            "/v1/chat/completions",
            "/v1/chat/completions/{completion_id}",
            "/v1/chat/completions/{completion_id}/messages",
            "/v1/embeddings",
            "/v1/images/generations",
            "/v1/images/edits",
            "/v1/images/variations",
            "/v1/moderations",
            "/v1/audio/speech",
            "/v1/audio/transcriptions",
            "/v1/audio/translations",
            "/v1/audio/voices",
            "/v1/audio/voice_consents",
            "/v1/audio/voice_consents/{consent_id}",
            "/v1/realtime/sessions",
            "/v1/realtime/transcription_sessions",
            "/v1/realtime/calls/{call_id}/accept",
            "/v1/realtime/calls/{call_id}/hangup",
            "/v1/realtime/calls/{call_id}/refer",
            "/v1/realtime/calls/{call_id}/reject",
            "/v1/files",
            "/v1/files/{file_id}",
            "/v1/files/{file_id}/content",
            "/v1/uploads",
            "/v1/uploads/{upload_id}/parts",
            "/v1/uploads/{upload_id}/complete",
            "/v1/uploads/{upload_id}/cancel",
            "/v1/batches",
            "/v1/batches/{batch_id}",
            "/v1/batches/{batch_id}/cancel",
            "/v1/fine_tuning/jobs",
            "/v1/fine_tuning/jobs/{fine_tuning_job_id}",
            "/v1/fine_tuning/jobs/{fine_tuning_job_id}/cancel",
            "/v1/fine_tuning/jobs/{fine_tuning_job_id}/checkpoints",
            "/v1/fine_tuning/jobs/{fine_tuning_job_id}/events",
            "/v1/fine_tuning/jobs/{fine_tuning_job_id}/pause",
            "/v1/fine_tuning/jobs/{fine_tuning_job_id}/resume",
            "/v1/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions",
            "/v1/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions/{permission_id}",
            "/v1/fine_tuning/alpha/graders/run",
            "/v1/fine_tuning/alpha/graders/validate",
            "/v1/evals",
            "/v1/evals/{eval_id}",
            "/v1/evals/{eval_id}/runs",
            "/v1/evals/{eval_id}/runs/{run_id}",
            "/v1/evals/{eval_id}/runs/{run_id}/output_items",
            "/v1/evals/{eval_id}/runs/{run_id}/output_items/{output_item_id}",
            "/v1/models",
            "/v1/models/{model}",
            "/v1/vector_stores",
            "/v1/vector_stores/{vector_store_id}",
            "/v1/vector_stores/{vector_store_id}/file_batches",
            "/v1/vector_stores/{vector_store_id}/file_batches/{batch_id}",
            "/v1/vector_stores/{vector_store_id}/file_batches/{batch_id}/cancel",
            "/v1/vector_stores/{vector_store_id}/file_batches/{batch_id}/files",
            "/v1/vector_stores/{vector_store_id}/files",
            "/v1/vector_stores/{vector_store_id}/files/{file_id}",
            "/v1/vector_stores/{vector_store_id}/files/{file_id}/content",
            "/v1/vector_stores/{vector_store_id}/items",
            "/v1/vector_stores/{vector_store_id}/search",
            "/v1/local/evals/text_expectation",
        ],
        "capabilities": f"http://{args.host}:{server.server_address[1]}/v1/oauth-capabilities",
    }, indent=2))
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
