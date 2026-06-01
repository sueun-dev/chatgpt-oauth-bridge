#!/usr/bin/env bash
set -euo pipefail
PYTHON_BIN="${PYTHON:-python3}"

# Publish gate. Run from a normal shell with GitHub network access.
# Use --push to push the current branch before the strict publish check.
# This gate is no-write so a committed tree stays clean while it runs.
"$PYTHON_BIN" bridge.py preflight --no-write

if [ "${1:-}" = "--push" ]; then
  branch="$(git branch --show-current)"
  if [ -z "$branch" ]; then
    echo "Could not determine current git branch." >&2
    exit 2
  fi
  if ! git push origin "$branch"; then
    if [ -n "${GITHUB_TOKEN:-${GH_TOKEN:-}}" ]; then
      echo "git push failed; trying GitHub API publish fallback with GITHUB_TOKEN/GH_TOKEN." >&2
      "$PYTHON_BIN" bridge.py publish-api --branch "$branch"
    else
      echo "git push failed and no GITHUB_TOKEN or GH_TOKEN is set for the API fallback." >&2
      echo "Run from a shell that can resolve github.com, or set GITHUB_TOKEN/GH_TOKEN and retry." >&2
      exit 1
    fi
  fi
  git fetch origin "refs/heads/$branch:refs/remotes/origin/$branch"
fi

"$PYTHON_BIN" bridge.py publish-check --no-write --strict
