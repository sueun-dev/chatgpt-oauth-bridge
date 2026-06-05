from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable

from classify_openai_path import classify, normalize_path
from generate_compatibility_guide import CATEGORY_ACTIONS


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", "dist", "build", ".next", ".cache"}
SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".wav",
    ".pcm16",
    ".pyc",
}

OPENAI_URL_RE = re.compile(r"https://api\.openai\.com/v1/[A-Za-z0-9_./{}-]+")
V1_PATH_RE = re.compile(r"(?P<quote>['\"])(/v1/[A-Za-z0-9_./{}-]+)(?P=quote)")
PY_SDK_CLIENT_ALIAS_RE = re.compile(
    r"(?m)(?:^|[^A-Za-z0-9_$])(?P<alias>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:Async)?OpenAI\s*\("
)
JS_SDK_CLIENT_ALIAS_RE = re.compile(
    r"(?m)(?:^|[^A-Za-z0-9_$])(?:const|let|var)\s+"
    r"(?P<alias>[A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*new\s+OpenAI\s*\("
)

SDK_METHOD_PATHS = {
    "client.responses.create": "/responses",
    "client.responses.compact": "/responses/compact",
    "client.responses.retrieve": "/responses/{response_id}",
    "client.responses.cancel": "/responses/{response_id}/cancel",
    "client.responses.delete": "/responses/{response_id}",
    "client.responses.input_tokens.create": "/responses/input_tokens",
    "client.responses.inputTokens.create": "/responses/input_tokens",
    "client.responses.input_items.list": "/responses/{response_id}/input_items",
    "client.responses.inputItems.list": "/responses/{response_id}/input_items",
    "client.completions.create": "/completions",
    "client.chat.completions.create": "/chat/completions",
    "client.chat.completions.retrieve": "/chat/completions/{completion_id}",
    "client.chat.completions.list": "/chat/completions",
    "client.chat.completions.update": "/chat/completions/{completion_id}",
    "client.chat.completions.delete": "/chat/completions/{completion_id}",
    "client.chat.completions.messages.list": "/chat/completions/{completion_id}/messages",
    "client.chatkit.sessions.create": "/chatkit/sessions",
    "client.chatkit.sessions.cancel": "/chatkit/sessions/{session_id}/cancel",
    "client.chatkit.threads.create": "/chatkit/threads",
    "client.chatkit.threads.retrieve": "/chatkit/threads/{thread_id}",
    "client.chatkit.threads.items.list": "/chatkit/threads/{thread_id}/items",
    "client.embeddings.create": "/embeddings",
    "client.images.generate": "/images/generations",
    "client.images.edit": "/images/edits",
    "client.images.create_variation": "/images/variations",
    "client.images.variations.create": "/images/variations",
    "client.audio.speech.create": "/audio/speech",
    "client.audio.transcriptions.create": "/audio/transcriptions",
    "client.audio.translations.create": "/audio/translations",
    "client.audio.voice_consents.create": "/audio/voice_consents",
    "client.audio.voice_consents.retrieve": "/audio/voice_consents/{consent_id}",
    "client.audio.voices.list": "/audio/voices",
    "client.files.create": "/files",
    "client.files.list": "/files",
    "client.files.retrieve": "/files/{file_id}",
    "client.files.content": "/files/{file_id}/content",
    "client.files.delete": "/files/{file_id}",
    "client.uploads.create": "/uploads",
    "client.uploads.parts.create": "/uploads/{upload_id}/parts",
    "client.uploads.complete": "/uploads/{upload_id}/complete",
    "client.uploads.cancel": "/uploads/{upload_id}/cancel",
    "client.batches.create": "/batches",
    "client.batches.list": "/batches",
    "client.batches.retrieve": "/batches/{batch_id}",
    "client.batches.cancel": "/batches/{batch_id}/cancel",
    "client.vector_stores.create": "/vector_stores",
    "client.vector_stores.list": "/vector_stores",
    "client.vector_stores.retrieve": "/vector_stores/{vector_store_id}",
    "client.vector_stores.search": "/vector_stores/{vector_store_id}/search",
    "client.vector_stores.files.create": "/vector_stores/{vector_store_id}/files",
    "client.vector_stores.files.list": "/vector_stores/{vector_store_id}/files",
    "client.vector_stores.file_batches.create": "/vector_stores/{vector_store_id}/file_batches",
    "client.vector_stores.file_batches.retrieve": "/vector_stores/{vector_store_id}/file_batches/{batch_id}",
    "client.vector_stores.file_batches.files.list": "/vector_stores/{vector_store_id}/file_batches/{batch_id}/files",
    "client.vector_stores.file_batches.cancel": "/vector_stores/{vector_store_id}/file_batches/{batch_id}/cancel",
    "client.vector_stores.files.retrieve": "/vector_stores/{vector_store_id}/files/{file_id}",
    "client.vector_stores.files.content": "/vector_stores/{vector_store_id}/files/{file_id}/content",
    "client.vector_stores.files.delete": "/vector_stores/{vector_store_id}/files/{file_id}",
    "client.evals.create": "/evals",
    "client.evals.list": "/evals",
    "client.evals.retrieve": "/evals/{eval_id}",
    "client.evals.update": "/evals/{eval_id}",
    "client.evals.delete": "/evals/{eval_id}",
    "client.evals.runs.create": "/evals/{eval_id}/runs",
    "client.evals.runs.list": "/evals/{eval_id}/runs",
    "client.evals.runs.retrieve": "/evals/{eval_id}/runs/{run_id}",
    "client.evals.runs.delete": "/evals/{eval_id}/runs/{run_id}",
    "client.evals.runs.output_items.list": "/evals/{eval_id}/runs/{run_id}/output_items",
    "client.evals.runs.output_items.retrieve": "/evals/{eval_id}/runs/{run_id}/output_items/{output_item_id}",
    "client.moderations.create": "/moderations",
    "client.models.list": "/models",
    "client.models.retrieve": "/models/{model}",
    "client.beta.assistants.create": "/assistants",
    "client.beta.assistants.list": "/assistants",
    "client.beta.assistants.retrieve": "/assistants/{assistant_id}",
    "client.beta.assistants.update": "/assistants/{assistant_id}",
    "client.beta.assistants.delete": "/assistants/{assistant_id}",
    "client.beta.threads.create": "/threads",
    "client.beta.threads.retrieve": "/threads/{thread_id}",
    "client.beta.threads.update": "/threads/{thread_id}",
    "client.beta.threads.delete": "/threads/{thread_id}",
    "client.beta.threads.messages.create": "/threads/{thread_id}/messages",
    "client.beta.threads.messages.list": "/threads/{thread_id}/messages",
    "client.beta.threads.messages.retrieve": "/threads/{thread_id}/messages/{message_id}",
    "client.beta.threads.messages.update": "/threads/{thread_id}/messages/{message_id}",
    "client.beta.threads.messages.delete": "/threads/{thread_id}/messages/{message_id}",
    "client.beta.threads.runs.create": "/threads/{thread_id}/runs",
    "client.beta.threads.runs.retrieve": "/threads/{thread_id}/runs/{run_id}",
    "client.beta.threads.runs.update": "/threads/{thread_id}/runs/{run_id}",
    "client.beta.threads.runs.cancel": "/threads/{thread_id}/runs/{run_id}/cancel",
    "client.beta.threads.runs.steps.list": "/threads/{thread_id}/runs/{run_id}/steps",
    "client.beta.threads.runs.steps.retrieve": "/threads/{thread_id}/runs/{run_id}/steps/{step_id}",
    "client.beta.threads.runs.submit_tool_outputs": "/threads/{thread_id}/runs/{run_id}/submit_tool_outputs",
    "client.beta.threads.create_and_run": "/threads/runs",
    "client.conversations.create": "/conversations",
    "client.conversations.retrieve": "/conversations/{conversation_id}",
    "client.conversations.items.list": "/conversations/{conversation_id}/items",
    "client.conversations.items.retrieve": "/conversations/{conversation_id}/items/{item_id}",
    "client.fine_tuning.jobs.create": "/fine_tuning/jobs",
    "client.fine_tuning.jobs.list": "/fine_tuning/jobs",
    "client.fine_tuning.jobs.retrieve": "/fine_tuning/jobs/{fine_tuning_job_id}",
    "client.fine_tuning.jobs.cancel": "/fine_tuning/jobs/{fine_tuning_job_id}/cancel",
    "client.fine_tuning.jobs.checkpoints.list": "/fine_tuning/jobs/{fine_tuning_job_id}/checkpoints",
    "client.fine_tuning.jobs.events.list": "/fine_tuning/jobs/{fine_tuning_job_id}/events",
    "client.fine_tuning.jobs.pause": "/fine_tuning/jobs/{fine_tuning_job_id}/pause",
    "client.fine_tuning.jobs.resume": "/fine_tuning/jobs/{fine_tuning_job_id}/resume",
    "client.fine_tuning.alpha.graders.run": "/fine_tuning/alpha/graders/run",
    "client.fine_tuning.alpha.graders.validate": "/fine_tuning/alpha/graders/validate",
    "client.fine_tuning.checkpoints.permissions.list": "/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions",
    "client.fine_tuning.checkpoints.permissions.delete": "/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions/{permission_id}",
    "client.containers.create": "/containers",
    "client.containers.retrieve": "/containers/{container_id}",
    "client.containers.delete": "/containers/{container_id}",
    "client.containers.files.create": "/containers/{container_id}/files",
    "client.containers.files.list": "/containers/{container_id}/files",
    "client.containers.files.retrieve": "/containers/{container_id}/files/{file_id}",
    "client.containers.files.content": "/containers/{container_id}/files/{file_id}/content",
    "client.realtime.calls.create": "/realtime/calls",
    "client.realtime.calls.accept": "/realtime/calls/{call_id}/accept",
    "client.realtime.calls.hangup": "/realtime/calls/{call_id}/hangup",
    "client.realtime.calls.refer": "/realtime/calls/{call_id}/refer",
    "client.realtime.calls.reject": "/realtime/calls/{call_id}/reject",
    "client.realtime.client_secrets.create": "/realtime/client_secrets",
    "client.realtime.translations.client_secrets.create": "/realtime/translations/client_secrets",
    "client.realtime.sessions.create": "/realtime/sessions",
    "client.realtime.transcription_sessions.create": "/realtime/transcription_sessions",
    "client.skills.list": "/skills",
    "client.skills.retrieve": "/skills/{skill_id}",
    "client.skills.content.retrieve": "/skills/{skill_id}/content",
    "client.skills.versions.list": "/skills/{skill_id}/versions",
    "client.skills.versions.retrieve": "/skills/{skill_id}/versions/{version}",
    "client.skills.versions.content.retrieve": "/skills/{skill_id}/versions/{version}/content",
    "client.videos.create": "/videos",
    "client.videos.retrieve": "/videos/{video_id}",
    "client.videos.content": "/videos/{video_id}/content",
    "client.videos.edits.create": "/videos/edits",
    "client.videos.extensions.create": "/videos/extensions",
    "client.videos.remix": "/videos/{video_id}/remix",
    "client.videos.characters.list": "/videos/characters",
    "client.videos.characters.retrieve": "/videos/characters/{character_id}",
}

SDK_METHOD_PATHS.update({
    "client.images.createVariation": "/images/variations",
    "client.audio.voiceConsents.create": "/audio/voice_consents",
    "client.audio.voiceConsents.retrieve": "/audio/voice_consents/{consent_id}",
    "client.vectorStores.create": "/vector_stores",
    "client.vectorStores.list": "/vector_stores",
    "client.vectorStores.retrieve": "/vector_stores/{vector_store_id}",
    "client.vectorStores.search": "/vector_stores/{vector_store_id}/search",
    "client.vectorStores.files.create": "/vector_stores/{vector_store_id}/files",
    "client.vectorStores.files.list": "/vector_stores/{vector_store_id}/files",
    "client.vectorStores.files.retrieve": "/vector_stores/{vector_store_id}/files/{file_id}",
    "client.vectorStores.files.content": "/vector_stores/{vector_store_id}/files/{file_id}/content",
    "client.vectorStores.files.delete": "/vector_stores/{vector_store_id}/files/{file_id}",
    "client.vectorStores.fileBatches.create": "/vector_stores/{vector_store_id}/file_batches",
    "client.vectorStores.fileBatches.retrieve": "/vector_stores/{vector_store_id}/file_batches/{batch_id}",
    "client.vectorStores.fileBatches.cancel": "/vector_stores/{vector_store_id}/file_batches/{batch_id}/cancel",
    "client.vectorStores.fileBatches.files.list": "/vector_stores/{vector_store_id}/file_batches/{batch_id}/files",
    "client.fineTuning.jobs.create": "/fine_tuning/jobs",
    "client.fineTuning.jobs.list": "/fine_tuning/jobs",
    "client.fineTuning.jobs.retrieve": "/fine_tuning/jobs/{fine_tuning_job_id}",
    "client.fineTuning.jobs.cancel": "/fine_tuning/jobs/{fine_tuning_job_id}/cancel",
    "client.fineTuning.jobs.checkpoints.list": "/fine_tuning/jobs/{fine_tuning_job_id}/checkpoints",
    "client.fineTuning.jobs.events.list": "/fine_tuning/jobs/{fine_tuning_job_id}/events",
    "client.fineTuning.jobs.pause": "/fine_tuning/jobs/{fine_tuning_job_id}/pause",
    "client.fineTuning.jobs.resume": "/fine_tuning/jobs/{fine_tuning_job_id}/resume",
    "client.fineTuning.alpha.graders.run": "/fine_tuning/alpha/graders/run",
    "client.fineTuning.alpha.graders.validate": "/fine_tuning/alpha/graders/validate",
    "client.fineTuning.checkpoints.permissions.list": "/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions",
    "client.fineTuning.checkpoints.permissions.delete": "/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions/{permission_id}",
    "client.realtime.clientSecrets.create": "/realtime/client_secrets",
    "client.realtime.translations.clientSecrets.create": "/realtime/translations/client_secrets",
    "client.realtime.transcriptionSessions.create": "/realtime/transcription_sessions",
})

SDK_METHOD_PATHS.update({
    "client.organization.admin_api_keys.list": "/organization/admin_api_keys",
    "client.organization.admin_api_keys.retrieve": "/organization/admin_api_keys/{key_id}",
    "client.organization.admin_api_keys.delete": "/organization/admin_api_keys/{key_id}",
    "client.organization.audit_logs.list": "/organization/audit_logs",
    "client.organization.certificates.list": "/organization/certificates",
    "client.organization.certificates.retrieve": "/organization/certificates/{certificate_id}",
    "client.organization.certificates.activate": "/organization/certificates/activate",
    "client.organization.certificates.deactivate": "/organization/certificates/deactivate",
    "client.organization.certificates.delete": "/organization/certificates/{certificate_id}",
    "client.organization.costs.list": "/organization/costs",
    "client.organization.data_retention.retrieve": "/organization/data_retention",
    "client.organization.groups.list": "/organization/groups",
    "client.organization.groups.retrieve": "/organization/groups/{group_id}",
    "client.organization.groups.roles.list": "/organization/groups/{group_id}/roles",
    "client.organization.groups.roles.delete": "/organization/groups/{group_id}/roles/{role_id}",
    "client.organization.groups.users.list": "/organization/groups/{group_id}/users",
    "client.organization.groups.users.delete": "/organization/groups/{group_id}/users/{user_id}",
    "client.organization.invites.list": "/organization/invites",
    "client.organization.invites.retrieve": "/organization/invites/{invite_id}",
    "client.organization.invites.delete": "/organization/invites/{invite_id}",
    "client.organization.projects.list": "/organization/projects",
    "client.organization.projects.retrieve": "/organization/projects/{project_id}",
    "client.organization.projects.archive": "/organization/projects/{project_id}/archive",
    "client.organization.projects.api_keys.list": "/organization/projects/{project_id}/api_keys",
    "client.organization.projects.api_keys.retrieve": "/organization/projects/{project_id}/api_keys/{api_key_id}",
    "client.organization.projects.api_keys.delete": "/organization/projects/{project_id}/api_keys/{api_key_id}",
    "client.organization.projects.certificates.list": "/organization/projects/{project_id}/certificates",
    "client.organization.projects.certificates.activate": "/organization/projects/{project_id}/certificates/activate",
    "client.organization.projects.certificates.deactivate": "/organization/projects/{project_id}/certificates/deactivate",
    "client.organization.projects.data_retention.retrieve": "/organization/projects/{project_id}/data_retention",
    "client.organization.projects.groups.list": "/organization/projects/{project_id}/groups",
    "client.organization.projects.groups.retrieve": "/organization/projects/{project_id}/groups/{group_id}",
    "client.organization.projects.hosted_tool_permissions.list": "/organization/projects/{project_id}/hosted_tool_permissions",
    "client.organization.projects.model_permissions.list": "/organization/projects/{project_id}/model_permissions",
    "client.organization.projects.rate_limits.list": "/organization/projects/{project_id}/rate_limits",
    "client.organization.projects.rate_limits.retrieve": "/organization/projects/{project_id}/rate_limits/{rate_limit_id}",
    "client.organization.projects.service_accounts.list": "/organization/projects/{project_id}/service_accounts",
    "client.organization.projects.service_accounts.retrieve": "/organization/projects/{project_id}/service_accounts/{service_account_id}",
    "client.organization.projects.service_accounts.delete": "/organization/projects/{project_id}/service_accounts/{service_account_id}",
    "client.organization.projects.spend_alerts.list": "/organization/projects/{project_id}/spend_alerts",
    "client.organization.projects.spend_alerts.retrieve": "/organization/projects/{project_id}/spend_alerts/{alert_id}",
    "client.organization.projects.users.list": "/organization/projects/{project_id}/users",
    "client.organization.projects.users.retrieve": "/organization/projects/{project_id}/users/{user_id}",
    "client.organization.roles.list": "/organization/roles",
    "client.organization.roles.retrieve": "/organization/roles/{role_id}",
    "client.organization.spend_alerts.list": "/organization/spend_alerts",
    "client.organization.spend_alerts.retrieve": "/organization/spend_alerts/{alert_id}",
    "client.organization.usage.audio_speeches.list": "/organization/usage/audio_speeches",
    "client.organization.usage.audio_transcriptions.list": "/organization/usage/audio_transcriptions",
    "client.organization.usage.code_interpreter_sessions.list": "/organization/usage/code_interpreter_sessions",
    "client.organization.usage.completions.list": "/organization/usage/completions",
    "client.organization.usage.embeddings.list": "/organization/usage/embeddings",
    "client.organization.usage.file_search_calls.list": "/organization/usage/file_search_calls",
    "client.organization.usage.images.list": "/organization/usage/images",
    "client.organization.usage.moderations.list": "/organization/usage/moderations",
    "client.organization.usage.vector_stores.list": "/organization/usage/vector_stores",
    "client.organization.usage.web_search_calls.list": "/organization/usage/web_search_calls",
    "client.organization.users.list": "/organization/users",
    "client.organization.users.retrieve": "/organization/users/{user_id}",
    "client.organization.users.delete": "/organization/users/{user_id}",
    "client.organization.users.roles.list": "/organization/users/{user_id}/roles",
    "client.organization.users.roles.delete": "/organization/users/{user_id}/roles/{role_id}",
    "client.projects.roles.list": "/projects/{project_id}/roles",
    "client.projects.roles.retrieve": "/projects/{project_id}/roles/{role_id}",
    "client.projects.groups.roles.list": "/projects/{project_id}/groups/{group_id}/roles",
    "client.projects.groups.roles.retrieve": "/projects/{project_id}/groups/{group_id}/roles/{role_id}",
    "client.projects.users.roles.list": "/projects/{project_id}/users/{user_id}/roles",
    "client.projects.users.roles.retrieve": "/projects/{project_id}/users/{user_id}/roles/{role_id}",
})

CLIENT_SDK_METHOD_PATHS = {
    method: api_path
    for method, api_path in SDK_METHOD_PATHS.items()
    if method.startswith("client.")
}

for method, api_path in list(CLIENT_SDK_METHOD_PATHS.items()):
    if not method.startswith("client."):
        continue
    suffix = method.split(".", 1)[1]
    for prefix in ("openai", "sdk", "ai"):
        SDK_METHOD_PATHS[f"{prefix}.{suffix}"] = api_path


def sdk_method_pattern(method: str) -> re.Pattern[str]:
    return re.compile(r"(?<![A-Za-z0-9_$])" + re.escape(method) + r"(?![A-Za-z0-9_$])")


SDK_METHOD_PATTERNS = {method: sdk_method_pattern(method) for method in SDK_METHOD_PATHS}


def local_extension_classification(token: str) -> Dict[str, Any] | None:
    normalized = normalize_path(token)
    if normalized.startswith("/oauth-"):
        return {
            "query": token,
            "normalized_path": normalized,
            "matched_path": normalized,
            "match_type": "local_extension",
            "ok": True,
            "category": "local_compat_or_chatgpt_backend_bridge",
            "decision": "Use local bridge",
            "action": "This is a local OAuth bridge metadata endpoint, not an official OpenAI API path. It is safe to call against the local proxy.",
            "support": "Local bridge metadata endpoint.",
            "evidence": "local_extension:oauth_metadata",
            "candidates": [],
        }
    if normalized == "/local/evals/text_expectation":
        return {
            "query": token,
            "normalized_path": normalized,
            "matched_path": normalized,
            "match_type": "local_extension",
            "ok": True,
            "category": "local_compat_or_chatgpt_backend_bridge",
            "decision": "Use local bridge",
            "action": "This is a local eval helper endpoint exposed by the OAuth bridge.",
            "support": "Local eval helper endpoint.",
            "evidence": "local_extension:local_eval_text_expectation",
            "candidates": [],
        }
    if re.match(r"^/vector_stores/[^/]+/items$", normalized):
        return {
            "query": token,
            "normalized_path": normalized,
            "matched_path": "/vector_stores/{vector_store_id}/items",
            "match_type": "local_extension_template",
            "ok": True,
            "category": "local_compat_or_chatgpt_backend_bridge",
            "decision": "Use local bridge",
            "action": "This is a local vector-store text insertion helper exposed by the OAuth bridge.",
            "support": "Local vector-store helper endpoint.",
            "evidence": "local_extension:vector_store_items",
            "candidates": [],
        }
    return None


def discover_sdk_aliases(text: str) -> set[str]:
    aliases = set()
    for pattern in (PY_SDK_CLIENT_ALIAS_RE, JS_SDK_CLIENT_ALIAS_RE):
        for match in pattern.finditer(text):
            aliases.add(match.group("alias"))
    return aliases


def sdk_methods_for_text(text: str) -> list[tuple[str, str, re.Pattern[str]]]:
    methods = [
        (method, api_path, SDK_METHOD_PATTERNS[method])
        for method, api_path in SDK_METHOD_PATHS.items()
    ]
    static_prefixes = {"client", "openai", "sdk", "ai"}
    for alias in sorted(discover_sdk_aliases(text) - static_prefixes):
        for client_method, api_path in CLIENT_SDK_METHOD_PATHS.items():
            suffix = client_method.split(".", 1)[1]
            method = f"{alias}.{suffix}"
            methods.append((method, api_path, sdk_method_pattern(method)))
    return methods


def text_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for item in path.rglob("*"):
        if item.is_dir():
            continue
        rel_parts = item.relative_to(path).parts if item.is_relative_to(path) else item.parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        if item.suffix.lower() in SKIP_SUFFIXES:
            continue
        yield item


def classify_token(token: str) -> Dict[str, Any]:
    local = local_extension_classification(token)
    if local:
        return local
    payload = classify(token)
    match = payload.get("match") if payload.get("ok") else None
    category = str(match.get("category")) if isinstance(match, dict) else "not_in_surface_audit"
    meta = CATEGORY_ACTIONS.get(category, {
        "label": "Not in surface audit",
        "action": "No matching OpenAI API path is recorded. Check spelling or refresh the surface audit.",
    })
    return {
        "query": token,
        "normalized_path": payload.get("normalized_path") or normalize_path(token),
        "matched_path": payload.get("matched_path"),
        "match_type": payload.get("match_type"),
        "ok": payload.get("ok"),
        "category": category,
        "decision": meta["label"],
        "action": meta["action"],
        "support": match.get("support") if isinstance(match, dict) else None,
        "evidence": match.get("evidence") if isinstance(match, dict) else None,
        "candidates": payload.get("candidates") or [],
    }


def record_finding(source: str, line: int | None, kind: str, token: str) -> Dict[str, Any]:
    classified = classify_token(token)
    classified.update({
        "source": source,
        "line": line,
        "kind": kind,
        "token": token,
    })
    return classified


def scan_text(path: Path) -> list[Dict[str, Any]]:
    findings: list[Dict[str, Any]] = []
    try:
        text = path.read_text(errors="ignore")
    except Exception as exc:
        return [{
            "source": str(path),
            "line": None,
            "kind": "read_error",
            "token": str(path),
            "ok": False,
            "category": "read_error",
            "decision": "Read error",
            "action": f"Could not read this file: {type(exc).__name__}: {exc}",
            "support": None,
            "evidence": None,
            "candidates": [],
        }]

    seen: set[tuple[int, str, str]] = set()
    sdk_patterns = sdk_methods_for_text(text)
    for line_no, line in enumerate(text.splitlines(), 1):
        for match in OPENAI_URL_RE.finditer(line):
            token = match.group(0)
            key = (line_no, "openai_url", token)
            if key not in seen:
                findings.append(record_finding(str(path), line_no, "openai_url", token))
                seen.add(key)
        for match in V1_PATH_RE.finditer(line):
            token = match.group(2)
            key = (line_no, "v1_path_literal", token)
            if key not in seen:
                findings.append(record_finding(str(path), line_no, "v1_path_literal", token))
                seen.add(key)
        for method, api_path, pattern in sdk_patterns:
            if not pattern.search(line):
                continue
            key = (line_no, "python_sdk_method", method)
            if key not in seen:
                finding = record_finding(str(path), line_no, "python_sdk_method", api_path)
                finding["token"] = method
                finding["sdk_api_path"] = api_path
                findings.append(finding)
                seen.add(key)
    return findings


def scan_item(item: str) -> list[Dict[str, Any]]:
    path = Path(item).expanduser()
    if path.exists():
        findings: list[Dict[str, Any]] = []
        for file_path in text_files(path):
            findings.extend(scan_text(file_path))
        return findings
    if item in SDK_METHOD_PATHS:
        finding = record_finding("<arg>", None, "sdk_method_argument", SDK_METHOD_PATHS[item])
        finding["token"] = item
        finding["sdk_api_path"] = SDK_METHOD_PATHS[item]
        return [finding]
    return [record_finding("<arg>", None, "argument", item)]


def build_report(items: list[str]) -> Dict[str, Any]:
    findings: list[Dict[str, Any]] = []
    for item in items:
        findings.extend(scan_item(item))

    category_counts = Counter(str(finding.get("category")) for finding in findings)
    boundary_categories = {
        "api_key_or_admin_key_required",
        "resource_bound_not_fully_verified",
        "official_route_auth_reached_but_not_complete",
        "not_available_current_deployment",
        "not_probed_directly",
        "not_in_surface_audit",
        "read_error",
    }
    blocking_findings = [
        finding for finding in findings
        if str(finding.get("category")) in boundary_categories
    ]
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "inputs": items,
        "finding_count": len(findings),
        "category_counts": dict(sorted(category_counts.items())),
        "usable_without_platform_key_count": sum(
            1
            for finding in findings
            if finding.get("category") in {
                "direct_official_oauth_verified",
                "local_compat_or_chatgpt_backend_bridge",
            }
        ),
        "blocked_or_unproven_count": len(blocking_findings),
        "findings": findings,
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "usage_check_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))

    lines = [
        "# OpenAI Usage Compatibility Check",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Inputs: `{', '.join(payload['inputs'])}`",
        f"- Findings: `{payload['finding_count']}`",
        f"- Usable without Platform key: `{payload['usable_without_platform_key_count']}`",
        f"- Blocked or unproven: `{payload['blocked_or_unproven_count']}`",
        "",
        "## Category Counts",
        "",
        "| Category | Count |",
        "|---|---:|",
    ]
    for category, count in payload["category_counts"].items():
        lines.append(f"| `{category}` | {count} |")
    lines.extend([
        "",
        "## Findings",
        "",
        "| Source | Line | Token | Path | Matched Path | Category | Decision | Evidence |",
        "|---|---:|---|---|---|---|---|---|",
    ])
    for finding in payload["findings"]:
        source = str(finding.get("source") or "").replace("|", "\\|")
        line = finding.get("line") if finding.get("line") is not None else ""
        token = str(finding.get("token") or "").replace("|", "\\|")
        path = str(finding.get("normalized_path") or "").replace("|", "\\|")
        matched_path = str(finding.get("matched_path") or "").replace("|", "\\|")
        category = str(finding.get("category") or "").replace("|", "\\|")
        decision = str(finding.get("decision") or "").replace("|", "\\|")
        evidence = str(finding.get("evidence") or "").replace("|", "\\|")
        lines.append(f"| `{source}` | {line} | `{token}` | `{path}` | `{matched_path}` | `{category}` | {decision} | `{evidence}` |")
    lines.append("")
    (REPORTS / "usage_check_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any], *, limit: int) -> None:
    print("OpenAI usage compatibility check")
    print(f"- findings: {payload['finding_count']}")
    print(f"- usable_without_platform_key: {payload['usable_without_platform_key_count']}")
    print(f"- blocked_or_unproven: {payload['blocked_or_unproven_count']}")
    for category, count in payload["category_counts"].items():
        print(f"- {category}: {count}")
    print()
    for finding in payload["findings"][:limit]:
        location = finding["source"]
        if finding.get("line") is not None:
            location += f":{finding['line']}"
        print(f"{location}")
        path = finding.get("normalized_path")
        matched_path = finding.get("matched_path")
        match_note = f" (matches {matched_path})" if matched_path and matched_path != path else ""
        print(f"  {finding['token']} -> {path}{match_note} [{finding.get('category')}]")
        print(f"  {finding.get('action')}")
    remaining = payload["finding_count"] - min(limit, payload["finding_count"])
    if remaining > 0:
        print(f"... {remaining} more findings in reports/usage_check_latest.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check OpenAI API paths or local source files against the OAuth bridge compatibility audit.")
    parser.add_argument("items", nargs="+", help="OpenAI API paths, full api.openai.com URLs, files, or directories to scan.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--limit", type=int, default=20, help="Number of findings to print in human output.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/usage_check_latest.*.")
    parser.add_argument("--fail-on-boundary", action="store_true", help="Exit non-zero when blocked or unproven paths are found.")
    args = parser.parse_args()

    payload = build_report(args.items)
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload, limit=max(args.limit, 0))
    if args.fail_on_boundary and payload["blocked_or_unproven_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
