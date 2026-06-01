from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List

from check_openai_usage import SDK_METHOD_PATHS, build_report, scan_text


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

CASES = [
    ("client.responses.create", "/responses", "local_compat_or_chatgpt_backend_bridge"),
    ("client.models.list", "/models", "local_compat_or_chatgpt_backend_bridge"),
    ("client.chatkit.sessions.create", "/chatkit/sessions", "local_compat_or_chatgpt_backend_bridge"),
    ("client.containers.retrieve", "/containers/{container_id}", "local_compat_or_chatgpt_backend_bridge"),
    ("client.containers.files.create", "/containers/{container_id}/files", "local_compat_or_chatgpt_backend_bridge"),
    ("client.conversations.create", "/conversations", "local_compat_or_chatgpt_backend_bridge"),
    ("client.conversations.items.retrieve", "/conversations/{conversation_id}/items/{item_id}", "local_compat_or_chatgpt_backend_bridge"),
    ("client.audio.voices.list", "/audio/voices", "local_compat_or_chatgpt_backend_bridge"),
    ("client.audio.voice_consents.create", "/audio/voice_consents", "local_compat_or_chatgpt_backend_bridge"),
    ("client.audio.voiceConsents.retrieve", "/audio/voice_consents/{consent_id}", "local_compat_or_chatgpt_backend_bridge"),
    ("client.audio.translations.create", "/audio/translations", "local_compat_or_chatgpt_backend_bridge"),
    ("client.images.edit", "/images/edits", "local_compat_or_chatgpt_backend_bridge"),
    ("client.images.variations.create", "/images/variations", "local_compat_or_chatgpt_backend_bridge"),
    ("client.realtime.client_secrets.create", "/realtime/client_secrets", "direct_official_oauth_verified"),
    ("client.realtime.sessions.create", "/realtime/sessions", "local_compat_or_chatgpt_backend_bridge"),
    ("client.realtime.transcription_sessions.create", "/realtime/transcription_sessions", "local_compat_or_chatgpt_backend_bridge"),
    ("client.skills.versions.content.retrieve", "/skills/{skill_id}/versions/{version}/content", "local_compat_or_chatgpt_backend_bridge"),
    ("client.videos.create", "/videos", "local_compat_or_chatgpt_backend_bridge"),
    ("client.videos.retrieve", "/videos/{video_id}", "local_compat_or_chatgpt_backend_bridge"),
    ("client.videos.content", "/videos/{video_id}/content", "local_compat_or_chatgpt_backend_bridge"),
    ("client.videos.edits.create", "/videos/edits", "local_compat_or_chatgpt_backend_bridge"),
    ("client.videos.extensions.create", "/videos/extensions", "local_compat_or_chatgpt_backend_bridge"),
    ("client.videos.remix", "/videos/{video_id}/remix", "local_compat_or_chatgpt_backend_bridge"),
    ("client.videos.characters.list", "/videos/characters", "local_compat_or_chatgpt_backend_bridge"),
    ("client.videos.characters.retrieve", "/videos/characters/{character_id}", "local_compat_or_chatgpt_backend_bridge"),
    ("client.organization.projects.list", "/organization/projects", "local_compat_or_chatgpt_backend_bridge"),
    ("client.organization.projects.archive", "/organization/projects/{project_id}/archive", "local_compat_or_chatgpt_backend_bridge"),
    ("client.organization.projects.api_keys.delete", "/organization/projects/{project_id}/api_keys/{api_key_id}", "local_compat_or_chatgpt_backend_bridge"),
    ("client.organization.admin_api_keys.list", "/organization/admin_api_keys", "local_compat_or_chatgpt_backend_bridge"),
    ("client.organization.costs.list", "/organization/costs", "local_compat_or_chatgpt_backend_bridge"),
    ("client.organization.usage.completions.list", "/organization/usage/completions", "local_compat_or_chatgpt_backend_bridge"),
    ("client.projects.roles.retrieve", "/projects/{project_id}/roles/{role_id}", "local_compat_or_chatgpt_backend_bridge"),
    ("client.projects.users.roles.list", "/projects/{project_id}/users/{user_id}/roles", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fine_tuning.alpha.graders.run", "/fine_tuning/alpha/graders/run", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fine_tuning.alpha.graders.validate", "/fine_tuning/alpha/graders/validate", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fine_tuning.jobs.create", "/fine_tuning/jobs", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fine_tuning.jobs.list", "/fine_tuning/jobs", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fine_tuning.jobs.retrieve", "/fine_tuning/jobs/{fine_tuning_job_id}", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fine_tuning.jobs.cancel", "/fine_tuning/jobs/{fine_tuning_job_id}/cancel", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fine_tuning.jobs.checkpoints.list", "/fine_tuning/jobs/{fine_tuning_job_id}/checkpoints", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fine_tuning.jobs.events.list", "/fine_tuning/jobs/{fine_tuning_job_id}/events", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fine_tuning.jobs.pause", "/fine_tuning/jobs/{fine_tuning_job_id}/pause", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fine_tuning.jobs.resume", "/fine_tuning/jobs/{fine_tuning_job_id}/resume", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fine_tuning.checkpoints.permissions.list", "/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fine_tuning.checkpoints.permissions.delete", "/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions/{permission_id}", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fineTuning.alpha.graders.run", "/fine_tuning/alpha/graders/run", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fineTuning.alpha.graders.validate", "/fine_tuning/alpha/graders/validate", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fineTuning.jobs.create", "/fine_tuning/jobs", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fineTuning.jobs.list", "/fine_tuning/jobs", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fineTuning.jobs.retrieve", "/fine_tuning/jobs/{fine_tuning_job_id}", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fineTuning.jobs.cancel", "/fine_tuning/jobs/{fine_tuning_job_id}/cancel", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fineTuning.jobs.checkpoints.list", "/fine_tuning/jobs/{fine_tuning_job_id}/checkpoints", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fineTuning.jobs.events.list", "/fine_tuning/jobs/{fine_tuning_job_id}/events", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fineTuning.jobs.pause", "/fine_tuning/jobs/{fine_tuning_job_id}/pause", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fineTuning.jobs.resume", "/fine_tuning/jobs/{fine_tuning_job_id}/resume", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fineTuning.checkpoints.permissions.list", "/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions", "local_compat_or_chatgpt_backend_bridge"),
    ("client.fineTuning.checkpoints.permissions.delete", "/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions/{permission_id}", "local_compat_or_chatgpt_backend_bridge"),
    ("client.realtime.transcriptionSessions.create", "/realtime/transcription_sessions", "local_compat_or_chatgpt_backend_bridge"),
    ("client.vectorStores.fileBatches.files.list", "/vector_stores/{vector_store_id}/file_batches/{batch_id}/files", "local_compat_or_chatgpt_backend_bridge"),
    ("/v1/oauth-boundary-playbook", "/oauth-boundary-playbook", "local_compat_or_chatgpt_backend_bridge"),
    ("/v1/vector_stores/vs_123/items", "/vector_stores/{vector_store_id}/items", "local_compat_or_chatgpt_backend_bridge"),
]

ALIAS_CASES = [
    ("openai_client.chatkit.sessions.create", "/chatkit/sessions", "local_compat_or_chatgpt_backend_bridge"),
    ("async_ai.organization.projects.list", "/organization/projects", "local_compat_or_chatgpt_backend_bridge"),
    ("media.videos.edits.create", "/videos/edits", "local_compat_or_chatgpt_backend_bridge"),
]


def build_alias_rows() -> List[Dict[str, Any]]:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        python_source = root / "alias_probe.py"
        python_source.write_text(
            "\n".join([
                "from openai import AsyncOpenAI, OpenAI",
                "openai_client = OpenAI()",
                "async_ai = AsyncOpenAI()",
                "openai_client.chatkit.sessions.create(model='gpt-5')",
                "async_ai.organization.projects.list()",
                "",
            ])
        )
        js_source = root / "alias_probe.js"
        js_source.write_text(
            "\n".join([
                "import OpenAI from 'openai';",
                "const media = new OpenAI();",
                "media.videos.edits.create({ model: 'sora-2' });",
                "",
            ])
        )
        findings = {}
        for source in (python_source, js_source):
            for finding in scan_text(source):
                token = finding.get("token")
                if isinstance(token, str):
                    findings[token] = finding

    rows: List[Dict[str, Any]] = []
    for token, expected_path, expected_category in ALIAS_CASES:
        finding = findings.get(token)
        matched_path = finding.get("matched_path") if finding else None
        category = finding.get("category") if finding else None
        rows.append({
            "token": token,
            "expected_matched_path": expected_path,
            "actual_matched_path": matched_path,
            "expected_category": expected_category,
            "actual_category": category,
            "status": "pass" if matched_path == expected_path and category == expected_category else "fail",
        })
    return rows


def build_verification() -> Dict[str, Any]:
    report = build_report([case[0] for case in CASES])
    alias_rows = build_alias_rows()
    surface = json.loads((REPORTS / "openai_surface_audit_latest.json").read_text())
    official_paths = {
        str(row.get("path"))
        for row in surface.get("rows", [])
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }
    mapped_paths = set(SDK_METHOD_PATHS.values())
    missing_paths = sorted(official_paths - mapped_paths)
    extra_paths = sorted(mapped_paths - official_paths)
    findings = {
        str(finding.get("token")): finding
        for finding in report.get("findings", [])
        if isinstance(finding, dict)
    }
    rows: List[Dict[str, Any]] = []
    for token, expected_path, expected_category in CASES:
        finding = findings.get(token)
        matched_path = finding.get("matched_path") if finding else None
        category = finding.get("category") if finding else None
        rows.append({
            "token": token,
            "expected_matched_path": expected_path,
            "actual_matched_path": matched_path,
            "expected_category": expected_category,
            "actual_category": category,
            "status": "pass" if matched_path == expected_path and category == expected_category else "fail",
        })
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "object": "oauth_compat.usage_scanner_verification",
        "checked": len(rows) + len(alias_rows),
        "official_paths": len(official_paths),
        "mapped_paths": len(mapped_paths),
        "missing_paths": missing_paths,
        "extra_paths": extra_paths,
        "ok": (
            all(row["status"] == "pass" for row in rows)
            and all(row["status"] == "pass" for row in alias_rows)
            and not missing_paths
            and not extra_paths
        ),
        "rows": rows,
        "alias_rows": alias_rows,
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "usage_scanner_coverage_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    lines = [
        "# Usage Scanner Coverage",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- OK: `{payload['ok']}`",
        f"- Checked: `{payload['checked']}`",
        f"- Official paths: `{payload['official_paths']}`",
        f"- SDK-mapped paths: `{payload['mapped_paths']}`",
        "",
        "## Path Coverage",
        "",
        f"- Missing paths: `{len(payload['missing_paths'])}`",
        f"- Extra paths: `{len(payload['extra_paths'])}`",
        "",
        "## Representative Cases",
        "",
        "| Status | Token | Matched Path | Category |",
        "|---|---|---|---|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| `{row['status']}` | `{row['token']}` | "
            f"`{row['actual_matched_path']}` | `{row['actual_category']}` |"
        )
    lines.extend([
        "",
        "## Alias Cases",
        "",
        "| Status | Token | Matched Path | Category |",
        "|---|---|---|---|",
    ])
    for row in payload["alias_rows"]:
        lines.append(
            f"| `{row['status']}` | `{row['token']}` | "
            f"`{row['actual_matched_path']}` | `{row['actual_category']}` |"
        )
    lines.append("")
    (REPORTS / "usage_scanner_coverage_latest.md").write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify scanner coverage for OpenAI API and SDK usage.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/usage_scanner_coverage_latest.*.")
    args = parser.parse_args()

    payload = build_verification()
    if not args.no_write:
        write_reports(payload)
    print("Usage scanner coverage:", "pass" if payload["ok"] else "fail")
    print(f"official_paths={payload['official_paths']} mapped_paths={payload['mapped_paths']}")
    if payload["missing_paths"]:
        print("missing_paths=" + ", ".join(payload["missing_paths"][:20]))
    if payload["extra_paths"]:
        print("extra_paths=" + ", ".join(payload["extra_paths"][:20]))
    for row in payload["rows"]:
        print(
            f"- {row['status']}: {row['token']} -> "
            f"{row['actual_matched_path']} [{row['actual_category']}]"
        )
    for row in payload["alias_rows"]:
        print(
            f"- {row['status']}: {row['token']} -> "
            f"{row['actual_matched_path']} [{row['actual_category']}]"
        )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
