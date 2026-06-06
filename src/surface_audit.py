"""Shared loader for the OpenAI surface audit report.

The canonical artifact is ``reports/openai_surface_audit_latest.json``. That
JSON is a generated file and is intentionally gitignored, so on a fresh clone
it is absent until ``python bridge.py audit`` is run. Its Markdown twin,
``reports/openai_surface_audit_latest.md``, *is* tracked in git and carries the
full per-path row set (path, category, support, evidence).

To keep every surface-aware command working on a fresh clone, this loader
transparently falls back to reconstructing the row set from the Markdown report
when the JSON is missing. Only when *both* artifacts are absent does it raise
``FileNotFoundError`` (the original behaviour).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
JSON_NAME = "openai_surface_audit_latest.json"
MARKDOWN_NAME = "openai_surface_audit_latest.md"

MARKDOWN_FALLBACK_WARNING = (
    "Reconstructed from reports/openai_surface_audit_latest.md; run "
    "`python bridge.py audit` to regenerate the full JSON report."
)


def _strip_code_cell(value: str) -> str:
    text = value.strip()
    if text.startswith("`") and text.endswith("`") and len(text) >= 2:
        return text[1:-1]
    return text


def rows_from_markdown(path: Path) -> List[Dict[str, Any]]:
    """Reconstruct surface rows from the tracked Markdown report."""
    rows: List[Dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        api_path = _strip_code_cell(cells[0])
        category = _strip_code_cell(cells[1])
        if not api_path.startswith("/"):
            continue
        rows.append(
            {
                "path": api_path,
                "category": category,
                "support": cells[2],
                "evidence": _strip_code_cell(cells[3]),
            }
        )
    return rows


def _payload_from_markdown(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = Counter(str(row.get("category") or "") for row in rows)
    return {
        "rows": rows,
        "category_counts": dict(sorted(counts.items())),
        "generated_at": None,
        "official_paths_count": None,
        "openapi_source": None,
        "source_warning": MARKDOWN_FALLBACK_WARNING,
        "matrix_started_at": None,
        "matrix_finished_at": None,
    }


def load_surface_payload() -> Dict[str, Any]:
    """Return the surface audit payload.

    Prefers the JSON report; falls back to reconstructing it from the tracked
    Markdown report so surface-aware commands work on a fresh clone before
    ``python bridge.py audit`` has been run.
    """
    json_path = REPORTS / JSON_NAME
    if json_path.exists():
        payload = json.loads(json_path.read_text())
        if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
            raise ValueError(f"Invalid surface audit report: {json_path}")
        return payload
    markdown_path = REPORTS / MARKDOWN_NAME
    if markdown_path.exists():
        rows = rows_from_markdown(markdown_path)
        if rows:
            return _payload_from_markdown(rows)
    raise FileNotFoundError(f"Missing surface audit report: {json_path}")


def load_surface_rows() -> List[Dict[str, Any]]:
    """Return only the surface rows (JSON preferred, Markdown fallback)."""
    payload = load_surface_payload()
    rows = payload.get("rows")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
