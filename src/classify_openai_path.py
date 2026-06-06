from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def normalize_path(value: str) -> str:
    text = value.strip()
    if not text:
        return text
    parsed = urlparse(text)
    if parsed.scheme and parsed.netloc:
        text = parsed.path
    else:
        text = text.split("?", 1)[0]
    if text.startswith("/v1/"):
        text = text[3:]
    elif text == "/v1":
        text = "/"
    if len(text) > 1 and text.endswith("/"):
        text = text.rstrip("/")
    if not text.startswith("/"):
        text = "/" + text
    return text


def load_rows() -> list[Dict[str, Any]]:
    path = REPORTS / "openai_surface_audit_latest.json"
    if path.exists():
        payload = json.loads(path.read_text())
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise ValueError(f"Invalid surface audit report: {path}")
        return [row for row in rows if isinstance(row, dict)]
    markdown_path = REPORTS / "openai_surface_audit_latest.md"
    if markdown_path.exists():
        rows = load_rows_from_markdown(markdown_path)
        if rows:
            return rows
    raise FileNotFoundError(f"Missing surface audit report: {path}")


def strip_code_cell(value: str) -> str:
    text = value.strip()
    if text.startswith("`") and text.endswith("`") and len(text) >= 2:
        return text[1:-1]
    return text


def load_rows_from_markdown(path: Path) -> list[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        api_path = strip_code_cell(cells[0])
        category = strip_code_cell(cells[1])
        if not api_path.startswith("/"):
            continue
        rows.append({
            "path": api_path,
            "category": category,
            "support": cells[2],
            "evidence": strip_code_cell(cells[3]),
        })
    return rows


def template_matches(template: str, wanted: str) -> bool:
    template_parts = [part for part in template.split("/") if part]
    wanted_parts = [part for part in wanted.split("/") if part]
    if len(template_parts) != len(wanted_parts):
        return False
    for template_part, wanted_part in zip(template_parts, wanted_parts):
        if template_part.startswith("{") and template_part.endswith("}"):
            if not wanted_part:
                return False
            continue
        if template_part != wanted_part:
            return False
    return True


def classify(value: str) -> Dict[str, Any]:
    wanted = normalize_path(value)
    rows = load_rows()
    for row in rows:
        if row.get("path") == wanted:
            return {
                "ok": True,
                "query": value,
                "normalized_path": wanted,
                "matched_path": row.get("path"),
                "match_type": "exact",
                "match": row,
                "candidates": [],
            }

    for row in rows:
        path = row.get("path")
        if isinstance(path, str) and "{" in path and template_matches(path, wanted):
            return {
                "ok": True,
                "query": value,
                "normalized_path": wanted,
                "matched_path": path,
                "match_type": "template",
                "match": row,
                "candidates": [],
            }

    candidates = []
    for row in rows:
        path = row.get("path")
        if not isinstance(path, str):
            continue
        if wanted in path or path in wanted or path.split("/{", 1)[0] == wanted.split("/{", 1)[0]:
            candidates.append(row)
    return {
        "ok": False,
        "query": value,
        "normalized_path": wanted,
        "matched_path": None,
        "match_type": None,
        "match": None,
        "candidates": candidates[:12],
    }


def print_human(payload: Dict[str, Any]) -> None:
    if payload["ok"]:
        row = payload["match"]
        matched = payload.get("matched_path")
        suffix = f" (matches {matched})" if matched and matched != payload["normalized_path"] else ""
        print(f"{payload['normalized_path']}: {row['category']}{suffix}")
        print(row["support"])
        print(f"Evidence: {row['evidence']}")
        return
    print(f"{payload['normalized_path']}: not found in current OpenAI surface audit")
    candidates = payload.get("candidates") or []
    if candidates:
        print("Closest recorded paths:")
        for row in candidates:
            print(f"- {row.get('path')}: {row.get('category')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify one OpenAI API path using the latest OAuth surface audit.")
    parser.add_argument("path", help="OpenAI API path, with or without /v1, or a full api.openai.com URL.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    payload = classify(args.path)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
