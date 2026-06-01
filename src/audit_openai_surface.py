from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable

import httpx


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DEFAULT_OPENAPI_URL = "https://app.stainless.com/api/spec/documented/openai/openapi.documented.yml"
FALLBACK_OPENAPI_URL = "https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml"


def extract_paths(openapi_yaml: str) -> list[str]:
    paths: list[str] = []
    in_paths = False
    for line in openapi_yaml.splitlines():
        if line == "paths:":
            in_paths = True
            continue
        if in_paths and line and not line.startswith(" "):
            break
        if not in_paths:
            continue
        match = re.match(r"^  ([\"']?/[^:\"']+[\"']?):\s*$", line)
        if not match:
            continue
        path = match.group(1).strip("\"'")
        if path not in paths:
            paths.append(path)
    return sorted(paths)


def fetch_openapi_paths(urls: Iterable[str]) -> tuple[list[str], str]:
    errors: list[str] = []
    for url in urls:
        try:
            response = httpx.get(url, timeout=httpx.Timeout(30.0), follow_redirects=True)
            if response.status_code != 200:
                errors.append(f"{url}: HTTP {response.status_code}")
                continue
            paths = extract_paths(response.text)
            if paths:
                return paths, url
            errors.append(f"{url}: no paths parsed")
        except Exception as exc:
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
    raise RuntimeError("Could not fetch or parse OpenAI OpenAPI paths. " + "; ".join(errors))


def load_result_statuses(path: Path) -> tuple[dict[str, str], dict[str, Any]]:
    if not path.exists():
        return {}, {}
    payload = json.loads(path.read_text())
    statuses: dict[str, str] = {}
    for result in payload.get("results", []) or []:
        name = result.get("name")
        status = result.get("status")
        if isinstance(name, str) and isinstance(status, str):
            statuses[name] = status
    return statuses, payload


def status_note(statuses: dict[str, str], test_name: str) -> str:
    status = statuses.get(test_name)
    return f"{test_name}={status}" if status else f"{test_name}=not-run"


def local_status_note(local_statuses: dict[str, dict[str, str]], *checks: tuple[str, str]) -> str:
    parts = []
    for report_name, test_name in checks:
        status = local_statuses.get(report_name, {}).get(test_name)
        parts.append(f"{report_name}:{test_name}={status or 'not-run'}")
    return "; ".join(parts)


def classify_path(path: str, statuses: dict[str, str], local_statuses: dict[str, dict[str, str]]) -> Dict[str, str]:
    def record(category: str, support: str, evidence: str) -> Dict[str, str]:
        return {"path": path, "category": category, "support": support, "evidence": evidence}

    if path == "/audio/transcriptions":
        return record(
            "direct_official_oauth_verified",
            "Official STT endpoint accepted the Codex OAuth token in the latest matrix.",
            status_note(statuses, "official_api_stt_with_oauth"),
        )
    if path == "/audio/translations":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Official audio translations are blocked; local /v1/audio/translations runs OAuth audio transcription, then translates the transcript to English with Codex text.",
            local_status_note(local_statuses, ("offline", "audio_translations_create")),
        )
    if path == "/audio/voices":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted custom voice creation requires eligible Platform credentials; local /v1/audio/voices exposes built-in voice metadata and local custom-voice metadata for SDK/app compatibility.",
            local_status_note(local_statuses, ("offline", "audio_voice_catalog")),
        )
    if path.startswith("/audio/voice_consents"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted voice consent upload/retrieval requires eligible Platform credentials; local /v1/audio/voice_consents stores consent metadata and recordings for SDK/app workflow compatibility.",
            local_status_note(local_statuses, ("offline", "audio_voice_catalog")),
        )
    if path == "/embeddings":
        return record(
            "direct_official_oauth_verified",
            "Official embeddings endpoint accepted the Codex OAuth token in the latest matrix.",
            status_note(statuses, "official_api_embeddings_with_oauth"),
        )
    if path == "/realtime/client_secrets":
        return record(
            "direct_official_oauth_verified",
            "Official Realtime client secret endpoint accepted the Codex OAuth token.",
            status_note(statuses, "official_api_realtime_with_oauth"),
        )
    if path == "/realtime/translations/client_secrets":
        return record(
            "direct_official_oauth_verified",
            "Official Realtime translation client secret endpoint accepted the Codex OAuth token.",
            status_note(statuses, "official_api_realtime_translation_client_secret_with_oauth"),
        )
    if path == "/realtime/calls":
        return record(
            "direct_official_oauth_verified",
            "Official Realtime WebRTC call creation accepted a realistic multipart SDP offer.",
            status_note(statuses, "official_api_realtime_calls_with_oauth"),
        )
    if path.startswith("/realtime/calls/"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Official call lifecycle routes need a real call id; local /v1/realtime/calls/{call_id}/{accept,hangup,refer,reject} records lifecycle state for SDK/app compatibility without claiming hosted mutation proof.",
            local_status_note(local_statuses, ("offline", "realtime_call_lifecycle")),
        )
    if path.startswith("/conversations"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted Conversations are not proven complete with ChatGPT/Codex OAuth; local /v1/conversations stores conversations and items on disk for SDK/app compatibility.",
            local_status_note(local_statuses, ("offline", "conversations_items")),
        )
    if path == "/realtime/sessions":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "The documented route returned invalid-url/not-routed in this deployment; local /v1/realtime/sessions aliases it to the OAuth-accepted /v1/realtime/client_secrets route and returns a session-shaped client secret response.",
            local_status_note(local_statuses, ("offline", "realtime_sessions_aliases")),
        )
    if path == "/realtime/transcription_sessions":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "The older route is not routed here; local /v1/realtime/transcription_sessions aliases transcription setup to OAuth /v1/realtime/client_secrets with session.type=transcription.",
            local_status_note(local_statuses, ("offline", "realtime_sessions_aliases")),
        )
    if path == "/responses":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Local /v1/responses is implemented through the ChatGPT/Codex responses backend with local retrieve/cancel/delete/input-items compatibility.",
            status_note(statuses, "codex_text_response"),
        )
    if path == "/responses/input_tokens":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted input-token counting remains a Platform API-key surface; local /v1/responses/input_tokens returns an explicit approximate estimate for app-side checks.",
            local_status_note(local_statuses, ("offline", "responses_input_tokens_estimate")),
        )
    if path == "/responses/compact":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted Responses compaction remains a Platform/API-key surface; local /v1/responses/compact returns an OpenAI SDK-shaped compaction object backed by Codex text and a local base64 payload.",
            local_status_note(local_statuses, ("offline", "responses_compact")),
        )
    response_lifecycle_paths = {
        "/responses/{response_id}",
        "/responses/{response_id}/cancel",
        "/responses/{response_id}/input_items",
    }
    if path in response_lifecycle_paths:
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted stored Responses are blocked; local retrieve/cancel/delete/input-items compatibility is implemented.",
            status_note(statuses, "official_api_responses_with_oauth"),
        )
    if path == "/chat/completions":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Local /v1/chat/completions maps messages to Codex text generation and stores local completions for retrieve/list/update/delete.",
            status_note(statuses, "codex_text_response"),
        )
    if path == "/completions":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted legacy Completions remain a Platform API-key surface; local /v1/completions maps prompt text to Codex text generation for legacy app compatibility.",
            local_status_note(local_statuses, ("offline", "completions_create")),
        )
    if path.startswith("/chat/completions/"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted stored chat completions are blocked; local retrieve/list/update/delete and message-list compatibility is implemented.",
            status_note(statuses, "official_api_chat_completions_with_oauth"),
        )
    if path == "/images/generations":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Image generation is implemented through the Codex image_generation tool.",
            status_note(statuses, "codex_image_generation"),
        )
    if path == "/images/edits":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted image edits are blocked; local /v1/images/edits describes the source image with Codex vision, then generates an edited image with the Codex image_generation tool.",
            local_status_note(local_statuses, ("offline", "images_edit")),
        )
    if path == "/images/variations":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted image variations are blocked; local /v1/images/variations describes the source image with Codex vision, then generates a variation with the Codex image_generation tool.",
            local_status_note(local_statuses, ("offline", "images_variation")),
        )
    if path == "/audio/speech":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Official TTS is blocked; the bridge can synthesize PCM16 through Realtime audio.",
            status_note(statuses, "official_api_tts_with_oauth"),
        )
    if path.startswith("/batches"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted batches are blocked; local batch processing over local proxy routes is implemented for JSONL requests.",
            status_note(statuses, "official_api_batches_list_with_oauth"),
        )
    if path.startswith("/files"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Platform files are blocked; ChatGPT backend file upload plus local metadata is available.",
            status_note(statuses, "official_api_files_list_with_oauth"),
        )
    if path.startswith("/containers"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted containers remain a Platform API-key surface; local /v1/containers stores container metadata and files on disk for SDK/app compatibility.",
            local_status_note(local_statuses, ("offline", "containers_files")),
        )
    if path.startswith("/chatkit"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted ChatKit remains a Platform API-key surface; local /v1/chatkit provides sessions, threads, and thread items for SDK/app compatibility.",
            local_status_note(local_statuses, ("offline", "chatkit_sessions_threads")),
        )
    if path.startswith("/skills"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted Skills remain a Platform API-key surface; local /v1/skills exposes installed Codex skills plus local skill bundles for SDK/app compatibility.",
            local_status_note(local_statuses, ("offline", "skills_registry")),
        )
    if path.startswith("/uploads"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted upload sessions are blocked; local uploads, parts, complete, and cancel are implemented, with completion creating a ChatGPT backend file.",
            status_note(statuses, "official_api_upload_create_cancel_with_oauth"),
        )
    if path.startswith("/vector_stores"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted vector stores are blocked; local vector stores, files, file batches, and search are implemented with OAuth embeddings.",
            status_note(statuses, "official_api_vector_stores_list_with_oauth"),
        )
    if path.startswith("/evals"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted eval resources are blocked; local evals, runs, output items, and text expectation checks are implemented.",
            status_note(statuses, "official_api_evals_list_with_oauth"),
        )
    if path.startswith("/fine_tuning/jobs") or path.startswith("/fine_tuning/checkpoints"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted fine-tuning training and admin checkpoint permission changes require Platform/Admin credentials; local /v1/fine_tuning jobs, events, checkpoints, and permission metadata are stored for SDK/app compatibility without training a model.",
            local_status_note(local_statuses, ("offline", "fine_tuning_jobs")),
        )
    if path in {"/fine_tuning/alpha/graders/run", "/fine_tuning/alpha/graders/validate"}:
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted fine-tuning jobs still require Platform credentials; local grader run/validate supports string_check and multi graders for preflight compatibility.",
            local_status_note(local_statuses, ("offline", "fine_tuning_graders")),
        )
    if path == "/models":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Official model list is blocked; Codex backend model discovery is available.",
            status_note(statuses, "codex_models"),
        )
    if path.startswith("/models/"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Official model retrieval is a Platform API-key route; local /v1/models/{model} maps to the Codex backend model catalog.",
            status_note(statuses, "official_api_models_list_with_oauth"),
        )
    if path.startswith("/assistants"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted Assistants remain a Platform API-key surface; local /v1/assistants create/list/retrieve/update/delete compatibility is implemented for local apps and SDK clients.",
            local_status_note(
                local_statuses,
                ("offline", "assistant_thread_run"),
                ("offline", "thread_run_steps"),
            ),
        )
    if path == "/threads" or path.startswith("/threads/"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted Threads and Runs remain Platform API-key surfaces; local threads, messages, runs, run steps, cancel, submit-tool-outputs, and create-and-run compatibility are implemented with Codex text for run output.",
            local_status_note(
                local_statuses,
                ("offline", "assistant_thread_run"),
                ("offline", "thread_run_steps"),
                ("offline", "thread_message_delete"),
            ),
        )
    if path == "/moderations":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted moderation is blocked; local heuristic moderation is implemented for app compatibility.",
            status_note(statuses, "official_api_moderation_with_oauth"),
        )
    if path.startswith("/videos"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted Sora/video rendering requires Platform credentials; local /v1/videos... stores video job/storyboard metadata and content manifests for SDK/app compatibility without rendering hosted MP4 video.",
            local_status_note(local_statuses, ("offline", "videos_storyboard_sandbox")),
        )
    if path.startswith("/organization/usage") or path == "/organization/costs":
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted organization usage and cost reports require Admin credentials; local /v1/organization/usage... and /v1/organization/costs return explicit local sandbox reports for SDK/app compatibility.",
            local_status_note(local_statuses, ("offline", "organization_project_sandbox")),
        )
    if path.startswith("/organization/") or path.startswith("/projects/"):
        return record(
            "local_compat_or_chatgpt_backend_bridge",
            "Hosted organization/project administration requires Admin credentials; local /v1/organization... and /v1/projects... return sandbox metadata and mutation-shaped responses for SDK/app compatibility without changing real org resources.",
            local_status_note(local_statuses, ("offline", "organization_project_sandbox")),
        )
    api_key_groups = (
        "/responses/",
    )
    if path.startswith(api_key_groups):
        return record(
            "api_key_or_admin_key_required",
            "No complete OAuth bridge is verified for this Platform resource.",
            "see latest OAuth matrix for the closest representative probe",
        )
    return record(
        "not_probed_directly",
        "No direct probe or compatibility mapping is recorded for this path yet.",
        "no matrix evidence",
    )


def load_existing_audit_paths(path: Path) -> tuple[list[str], str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing existing audit report for fallback: {path}")
    payload = json.loads(path.read_text())
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError(f"Existing audit report has no rows list: {path}")
    paths = [
        row.get("path")
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    ]
    if not paths:
        raise ValueError(f"Existing audit report has no reusable paths: {path}")
    source = str(payload.get("openapi_source") or "unknown")
    while source.startswith("existing-report:"):
        source = source.removeprefix("existing-report:")
    generated_at = str(payload.get("generated_at") or "unknown")
    return sorted(set(paths)), source, generated_at


def write_reports(
    rows: list[Dict[str, str]],
    source_url: str,
    matrix_payload: dict[str, Any],
    *,
    source_warning: str | None = None,
) -> None:
    REPORTS.mkdir(exist_ok=True)
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    counts = Counter(row["category"] for row in rows)
    payload = {
        "generated_at": generated_at,
        "openapi_source": source_url,
        "official_paths_count": len(rows),
        "matrix_started_at": matrix_payload.get("started_at"),
        "matrix_finished_at": matrix_payload.get("finished_at"),
        "category_counts": dict(sorted(counts.items())),
        "source_warning": source_warning,
        "rows": rows,
    }
    (REPORTS / "openai_surface_audit_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))

    lines = [
        "# OpenAI API Surface Audit",
        "",
        f"- Generated: `{generated_at}`",
        f"- OpenAPI source: `{source_url}`",
        f"- Official paths parsed: `{len(rows)}`",
        f"- Matrix report: `reports/latest.json` from `{matrix_payload.get('started_at')}` to `{matrix_payload.get('finished_at')}`",
    ]
    if source_warning:
        lines.append(f"- Source warning: {source_warning}")
    lines.extend([
        "",
        "## Bottom Line",
        "",
        "This bridge does not make every OpenAI Platform endpoint available through ChatGPT/Codex OAuth. It verifies a small set of direct OAuth-accepted official routes, provides local or ChatGPT-backend compatibility for common app workflows, and marks the remaining Platform/Admin resources as API-key/Admin-key boundaries unless current evidence says otherwise.",
        "",
        "## Category Counts",
        "",
        "| Category | Paths |",
        "|---|---:|",
    ])
    for category, count in sorted(counts.items()):
        lines.append(f"| `{category}` | {count} |")
    lines.extend([
        "",
        "## Full Path Classification",
        "",
        "| Path | Category | Support | Evidence |",
        "|---|---|---|---|",
    ])
    for row in rows:
        support = row["support"].replace("|", "\\|")
        evidence = row["evidence"].replace("|", "\\|")
        lines.append(f"| `{row['path']}` | `{row['category']}` | {support} | `{evidence}` |")
    lines.append("")
    (REPORTS / "openai_surface_audit_latest.md").write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare OpenAI's documented API surface with current OAuth bridge coverage.")
    parser.add_argument("--openapi-url", default=DEFAULT_OPENAPI_URL, help="OpenAPI YAML URL to parse.")
    parser.add_argument("--matrix", default=str(REPORTS / "latest.json"), help="Path to a run_oauth_matrix JSON report.")
    parser.add_argument(
        "--no-existing-fallback",
        action="store_true",
        help="Fail instead of reusing reports/openai_surface_audit_latest.json when the OpenAPI spec cannot be fetched.",
    )
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/openai_surface_audit_latest.*.")
    args = parser.parse_args()

    urls = [args.openapi_url]
    if args.openapi_url != FALLBACK_OPENAPI_URL:
        urls.append(FALLBACK_OPENAPI_URL)
    source_warning = None
    try:
        paths, source_url = fetch_openapi_paths(urls)
    except Exception as exc:
        if args.no_existing_fallback:
            raise
        paths, existing_source, existing_generated_at = load_existing_audit_paths(
            REPORTS / "openai_surface_audit_latest.json"
        )
        source_url = f"existing-report:{existing_source}"
        source_warning = (
            "Could not refresh the OpenAPI source in this environment; "
            f"reused path list from reports/openai_surface_audit_latest.json generated at {existing_generated_at}. "
            f"Fetch error: {type(exc).__name__}: {exc}"
        )
    statuses, matrix_payload = load_result_statuses(Path(args.matrix))
    proxy_statuses, _proxy_payload = load_result_statuses(REPORTS / "proxy_smoke_latest.json")
    sdk_statuses, _sdk_payload = load_result_statuses(REPORTS / "openai_sdk_proxy_smoke_latest.json")
    offline_statuses, _offline_payload = load_result_statuses(REPORTS / "router_offline_smoke_latest.json")
    local_statuses = {
        "proxy": proxy_statuses,
        "sdk": sdk_statuses,
        "offline": offline_statuses,
    }
    rows = [classify_path(path, statuses, local_statuses) for path in paths]
    if not args.no_write:
        write_reports(rows, source_url, matrix_payload, source_warning=source_warning)
    print(json.dumps({
        "openapi_source": source_url,
        "official_paths_count": len(rows),
        "category_counts": dict(sorted(Counter(row["category"] for row in rows).items())),
        "source_warning": source_warning,
        "report": str(REPORTS / "openai_surface_audit_latest.md"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
