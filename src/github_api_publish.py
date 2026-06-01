from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
GITHUB_API = "https://api.github.com"


def run_git(args: list[str], *, check: bool = True, text: bool = True) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        check=False,
    )
    if check and proc.returncode != 0:
        stderr = proc.stderr if isinstance(proc.stderr, str) else proc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr.strip()}")
    return proc


def parse_repo(origin: str) -> str:
    origin = origin.strip()
    patterns = [
        r"^https://github\.com/([^/]+/[^/]+?)(?:\.git)?$",
        r"^git@github\.com:([^/]+/[^/]+?)(?:\.git)?$",
        r"^ssh://git@github\.com/([^/]+/[^/]+?)(?:\.git)?$",
    ]
    for pattern in patterns:
        match = re.match(pattern, origin)
        if match:
            return match.group(1)
    raise ValueError(f"Cannot parse GitHub repository from origin URL: {origin}")


def token_from_env(*, required: bool = True) -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    if not required:
        return ""
    raise RuntimeError("Set GITHUB_TOKEN or GH_TOKEN before using GitHub API publish.")


def api_request(repo: str, token: str, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "chatgpt-oauth-bridge-publisher",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{GITHUB_API}/repos/{repo}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {method} {path} failed with HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API {method} {path} failed: {exc}") from exc
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"GitHub API {method} {path} did not return a JSON object.")
    return parsed


def current_branch() -> str:
    branch = run_git(["branch", "--show-current"]).stdout.strip()
    if not branch:
        raise RuntimeError("Could not determine current git branch.")
    return branch


def local_tracking_sha(branch: str) -> str:
    proc = run_git(["rev-parse", f"origin/{branch}"], check=False)
    sha = proc.stdout.strip()
    if proc.returncode == 0 and sha:
        return sha
    raise RuntimeError(f"Could not read local tracking ref origin/{branch}.")


def ensure_clean_tree() -> None:
    status = run_git(["status", "--porcelain=v1"]).stdout.strip()
    if status:
        raise RuntimeError("Refusing GitHub API publish because the worktree is dirty:\n" + status)


def diff_paths(base_sha: str, head_sha: str) -> list[str]:
    proc = run_git(["diff", "--name-only", "-z", f"{base_sha}..{head_sha}"])
    raw = proc.stdout
    return [path for path in raw.split("\0") if path]


def local_tree_entry(path: str, token: str, repo: str) -> dict[str, Any]:
    ls = run_git(["ls-tree", "HEAD", "--", path]).stdout.strip()
    if not ls:
        return {"path": path, "mode": "100644", "type": "blob", "sha": None}
    meta, _tab, _name = ls.partition("\t")
    mode, kind, _sha = meta.split()
    blob_proc = run_git(["show", f"HEAD:{path}"], text=False)
    data = blob_proc.stdout
    entry: dict[str, Any] = {"path": path, "mode": mode, "type": kind}
    if kind != "blob":
        raise RuntimeError(f"Unsupported changed git object type for {path}: {kind}")
    try:
        entry["content"] = data.decode("utf-8")
    except UnicodeDecodeError:
        blob = api_request(
            repo,
            token,
            "POST",
            "/git/blobs",
            {"content": base64.b64encode(data).decode("ascii"), "encoding": "base64"},
        )
        entry["sha"] = blob["sha"]
    return entry


def remote_sha_for_branch(repo: str, token: str, branch: str, dry_run: bool) -> tuple[str, str, str]:
    try:
        remote_ref = api_request(repo, token, "GET", f"/git/ref/heads/{branch}")
        remote_sha = remote_ref.get("object", {}).get("sha")
        if isinstance(remote_sha, str) and remote_sha:
            return remote_sha, "github_api", ""
        raise RuntimeError(f"Could not read remote heads/{branch} SHA from GitHub.")
    except Exception as exc:
        if not dry_run:
            raise
        local_sha = local_tracking_sha(branch)
        warning = (
            f"GitHub API ref lookup failed during dry-run; using local origin/{branch} "
            f"tracking ref instead. Error: {exc}"
        )
        return local_sha, "local_tracking_ref", warning


def tree_sha_for_commit(repo: str, token: str, commit_sha: str, remote_source: str) -> tuple[str, str]:
    if remote_source == "github_api":
        commit = api_request(repo, token, "GET", f"/git/commits/{commit_sha}")
        tree_sha = commit.get("tree", {}).get("sha")
        if isinstance(tree_sha, str) and tree_sha:
            return tree_sha, "github_api"
        raise RuntimeError(f"Could not read tree SHA for remote commit {commit_sha}.")
    return run_git(["rev-parse", f"{commit_sha}^{{tree}}"]).stdout.strip(), "local_git"


def build_payload(repo: str, token: str, branch: str, dry_run: bool) -> dict[str, Any]:
    ensure_clean_tree()
    head_sha = run_git(["rev-parse", "HEAD"]).stdout.strip()
    remote_sha, remote_source, remote_warning = remote_sha_for_branch(repo, token, branch, dry_run)
    ancestor = run_git(["merge-base", "--is-ancestor", remote_sha, "HEAD"], check=False)
    if ancestor.returncode != 0:
        raise RuntimeError(
            f"Remote {branch} at {remote_sha} is not an ancestor of local HEAD {head_sha}. "
            "Fetch/rebase first; refusing to publish over unknown remote work."
        )
    paths = diff_paths(remote_sha, head_sha)
    base_tree_sha, base_tree_source = tree_sha_for_commit(repo, token, remote_sha, remote_source)
    message = run_git(["log", "-1", "--pretty=%B", "HEAD"]).stdout.strip()
    if not message:
        message = "Publish OAuth bridge update"
    return {
        "repo": repo,
        "branch": branch,
        "local_head": head_sha,
        "remote_head": remote_sha,
        "remote_source": remote_source,
        "remote_warning": remote_warning,
        "base_tree": base_tree_sha,
        "base_tree_source": base_tree_source,
        "message": message,
        "changed_paths": paths,
        "dry_run": dry_run,
    }


def publish(payload: dict[str, Any], repo: str, token: str) -> dict[str, Any]:
    tree_entries = [local_tree_entry(path, token, repo) for path in payload["changed_paths"]]
    tree = api_request(
        repo,
        token,
        "POST",
        "/git/trees",
        {"base_tree": payload["base_tree"], "tree": tree_entries},
    )
    tree_sha = tree.get("sha")
    if not isinstance(tree_sha, str):
        raise RuntimeError("GitHub did not return a tree SHA.")
    commit = api_request(
        repo,
        token,
        "POST",
        "/git/commits",
        {"message": payload["message"], "tree": tree_sha, "parents": [payload["remote_head"]]},
    )
    commit_sha = commit.get("sha")
    if not isinstance(commit_sha, str):
        raise RuntimeError("GitHub did not return a commit SHA.")
    api_request(
        repo,
        token,
        "PATCH",
        f"/git/refs/heads/{payload['branch']}",
        {"sha": commit_sha, "force": False},
    )
    return {
        **payload,
        "published": True,
        "remote_commit": commit_sha,
        "remote_url": f"https://github.com/{repo}/commit/{commit_sha}",
    }


def print_human(payload: dict[str, Any]) -> None:
    print("GitHub API publish:", "dry-run" if payload.get("dry_run") else "published")
    print(f"repo={payload['repo']} branch={payload['branch']}")
    print(f"local_head={payload['local_head']}")
    print(f"remote_head_before={payload['remote_head']}")
    print(f"remote_source={payload.get('remote_source')}")
    print(f"base_tree_source={payload.get('base_tree_source')}")
    if payload.get("remote_warning"):
        print(f"warning={payload['remote_warning']}")
    print(f"changed_paths={len(payload['changed_paths'])}")
    if payload.get("remote_commit"):
        print(f"remote_commit={payload['remote_commit']}")
        print(f"url={payload['remote_url']}")
    else:
        for path in payload["changed_paths"][:40]:
            print(f"- {path}")
        if len(payload["changed_paths"]) > 40:
            print(f"- ... {len(payload['changed_paths']) - 40} more")


def write_reports(payload: dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "github_api_publish_plan_latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    lines = [
        "# GitHub API Publish Plan",
        "",
        f"- Mode: `{'dry-run' if payload.get('dry_run') else 'published'}`",
        f"- Repository: `{payload.get('repo')}`",
        f"- Branch: `{payload.get('branch')}`",
        f"- Local HEAD: `{payload.get('local_head')}`",
        f"- Remote HEAD before: `{payload.get('remote_head')}`",
        f"- Remote source: `{payload.get('remote_source')}`",
        f"- Base tree source: `{payload.get('base_tree_source')}`",
        f"- Changed paths: `{len(payload.get('changed_paths') or [])}`",
    ]
    if payload.get("remote_warning"):
        lines.append(f"- Warning: {payload['remote_warning']}")
    if payload.get("remote_commit"):
        lines.extend([
            f"- Remote commit: `{payload.get('remote_commit')}`",
            f"- Remote URL: {payload.get('remote_url')}",
        ])
    lines.extend(["", "## Changed Paths", ""])
    for path in payload.get("changed_paths") or []:
        lines.append(f"- `{path}`")
    lines.append("")
    (REPORTS / "github_api_publish_plan_latest.md").write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the local clean HEAD to GitHub using the Git data API.")
    parser.add_argument("--repo", help="Repository in owner/name form. Defaults to parsing origin.")
    parser.add_argument("--branch", help="Branch to update. Defaults to the current branch.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and list changed paths without writing to GitHub.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports/github_api_publish_plan_latest.*.")
    args = parser.parse_args()

    try:
        token = token_from_env(required=not args.dry_run)
        origin = run_git(["remote", "get-url", "origin"]).stdout.strip()
        repo = args.repo or parse_repo(origin)
        branch = args.branch or current_branch()
        payload = build_payload(repo, token, branch, args.dry_run)
        if not args.dry_run:
            payload = publish(payload, repo, token)
        if not args.no_write:
            write_reports(payload)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print_human(payload)
        return 0
    except Exception as exc:
        print(f"GitHub API publish failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
