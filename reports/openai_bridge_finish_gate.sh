#!/usr/bin/env bash
set -euo pipefail

# End-to-end gate. Run from a normal shell with GitHub network access,
# ChatGPT/Codex network access, and localhost bind permission.
publish_args=()
if [ "${1:-}" = "--push" ]; then
  publish_args=(--push)
  shift
fi

bash reports/openai_bridge_publish_gate.sh "${publish_args[@]}"
bash reports/openai_bridge_launch_gate.sh "$@"
