from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

SOURCE_PREFIXES = ("src/",)
SOURCE_FILES = {"bridge.py", "setup_oauth.py", "requirements.txt"}
DOC_SUFFIXES = (".md",)
REPORT_SUFFIXES = (".md", ".csv", ".sh", ".example")


def run_git(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout.rstrip("\n")


def classify_path(path: str) -> str:
    if path in SOURCE_FILES or path.startswith(SOURCE_PREFIXES):
        return "source"
    if path.startswith("reports/") and path.endswith(REPORT_SUFFIXES):
        return "report"
    if path.endswith(DOC_SUFFIXES):
        return "doc"
    return "other"


def git_status_rows() -> list[dict[str, Any]]:
    code, output = run_git(["status", "--porcelain=v1"])
    if code != 0:
        return [{"status": "!!", "path": "", "category": "git_error", "raw": output}]
    rows: list[dict[str, Any]] = []
    for line in output.splitlines():
        if not line:
            continue
        status = line[:2]
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        rows.append({
            "status": status,
            "path": path,
            "category": classify_path(path),
            "raw": line,
        })
    return rows


def branch_info() -> dict[str, Any]:
    _, branch = run_git(["branch", "--show-current"])
    _, head = run_git(["rev-parse", "HEAD"])
    upstream_code, upstream = run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    upstream_head = ""
    ahead_behind = ""
    if upstream_code == 0 and upstream:
        _, upstream_head = run_git(["rev-parse", upstream])
        _, ahead_behind = run_git(["rev-list", "--left-right", "--count", f"{upstream}...HEAD"])
    remote_code, remote = run_git(["remote", "get-url", "origin"])
    return {
        "branch": branch,
        "head": head,
        "upstream": upstream if upstream_code == 0 else "",
        "upstream_head": upstream_head,
        "origin": remote if remote_code == 0 else "",
        "ahead_behind": ahead_behind,
        "head_matches_upstream": bool(head and upstream_head and head == upstream_head),
    }


def build_report() -> Dict[str, Any]:
    rows = git_status_rows()
    info = branch_info()
    changed = [row for row in rows if row["category"] != "git_error"]
    untracked_source = [row["path"] for row in changed if row["status"] == "??" and row["category"] == "source"]
    modified_source = [row["path"] for row in changed if row["status"] != "??" and row["category"] == "source"]
    untracked_reports = [row["path"] for row in changed if row["status"] == "??" and row["category"] == "report"]
    modified_reports = [row["path"] for row in changed if row["status"] != "??" and row["category"] == "report"]
    doc_changes = [row["path"] for row in changed if row["category"] == "doc"]
    other_changes = [row["path"] for row in changed if row["category"] == "other"]

    publish_ready = not changed and info.get("head_matches_upstream") is True
    local_tree_ready = not untracked_source

    if publish_ready:
        bottom_line = "Published tree matches the configured upstream branch."
    elif untracked_source:
        bottom_line = "Not publish-ready: source entrypoints exist only in the local worktree and are not tracked by git."
    elif changed:
        bottom_line = "Not publish-ready: local tracked or report/doc changes have not been committed and pushed."
    else:
        bottom_line = "Not publish-ready: local HEAD does not match the configured upstream branch."

    next_actions = []
    if untracked_source:
        next_actions.append("Stage the new source files before publishing, especially bridge.py and src/*.py helpers.")
    if modified_source or doc_changes or modified_reports or untracked_reports:
        next_actions.append("Review the diff, commit the intended source/docs/reports, then push to origin.")
    if not info.get("head_matches_upstream"):
        next_actions.append("Run bash reports/openai_bridge_publish_gate.sh --push from a networked shell, or push the release commit manually and refresh origin/main.")
    if not next_actions:
        next_actions.append("Run python bridge.py live-check from a normal local shell before launch-ready claims.")

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "publish_ready": publish_ready,
        "local_tree_ready": local_tree_ready,
        "bottom_line": bottom_line,
        "branch": info,
        "counts": {
            "changed_total": len(changed),
            "untracked_source": len(untracked_source),
            "modified_source": len(modified_source),
            "untracked_reports": len(untracked_reports),
            "modified_reports": len(modified_reports),
            "doc_changes": len(doc_changes),
            "other_changes": len(other_changes),
        },
        "untracked_source": untracked_source,
        "modified_source": modified_source,
        "untracked_reports": untracked_reports,
        "modified_reports": modified_reports,
        "doc_changes": doc_changes,
        "other_changes": other_changes,
        "next_actions": next_actions,
    }


def write_reports(payload: Dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "publish_check_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    branch = payload["branch"]
    lines = [
        "# Publish Check",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Publish ready: `{payload['publish_ready']}`",
        f"- Local tree ready: `{payload['local_tree_ready']}`",
        f"- Bottom line: {payload['bottom_line']}",
        "",
        "## Branch",
        "",
        f"- Branch: `{branch.get('branch')}`",
        f"- Origin: `{branch.get('origin')}`",
        f"- Upstream: `{branch.get('upstream')}`",
        f"- Ahead/behind: `{branch.get('ahead_behind')}`",
        f"- HEAD matches upstream: `{branch.get('head_matches_upstream')}`",
        "",
        "## Counts",
        "",
        "| Bucket | Count |",
        "|---|---:|",
    ]
    for key, value in payload["counts"].items():
        lines.append(f"| `{key}` | {value} |")
    for title, key in [
        ("Untracked Source", "untracked_source"),
        ("Modified Source", "modified_source"),
        ("Doc Changes", "doc_changes"),
        ("Untracked Reports", "untracked_reports"),
        ("Modified Reports", "modified_reports"),
        ("Other Changes", "other_changes"),
    ]:
        items = payload.get(key) or []
        lines.extend(["", f"## {title}", ""])
        if items:
            for item in items[:80]:
                lines.append(f"- `{item}`")
            if len(items) > 80:
                lines.append(f"- ... {len(items) - 80} more")
        else:
            lines.append("- None")
    lines.extend(["", "## Next Actions", ""])
    for action in payload["next_actions"]:
        lines.append(f"- {action}")
    lines.append("")
    (REPORTS / "publish_check_latest.md").write_text("\n".join(lines))


def print_human(payload: Dict[str, Any]) -> None:
    print("OAuth bridge publish check:", "ready" if payload["publish_ready"] else "not ready")
    print(payload["bottom_line"])
    print()
    branch = payload["branch"]
    print(f"branch={branch.get('branch')} upstream={branch.get('upstream')}")
    print(f"head={branch.get('head')}")
    print(f"upstream_head={branch.get('upstream_head')}")
    print(f"head_matches_upstream={branch.get('head_matches_upstream')}")
    counts = payload["counts"]
    print(
        "changes="
        f"total={counts['changed_total']}; "
        f"untracked_source={counts['untracked_source']}; "
        f"modified_source={counts['modified_source']}; "
        f"docs={counts['doc_changes']}; "
        f"reports={counts['untracked_reports'] + counts['modified_reports']}"
    )
    if payload["untracked_source"]:
        print()
        print("Untracked source:")
        for path in payload["untracked_source"][:20]:
            print(f"- {path}")
    print()
    print("Next actions:")
    for action in payload["next_actions"]:
        print(f"- {action}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether local OAuth bridge work is ready to publish to GitHub.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/publish_check_latest.*.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless the local tree matches the upstream branch.")
    args = parser.parse_args()

    payload = build_report()
    if not args.no_write:
        write_reports(payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human(payload)
    if args.strict and not payload["publish_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
