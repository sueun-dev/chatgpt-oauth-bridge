#!/usr/bin/env bash
set -euo pipefail
PYTHON_BIN="${PYTHON:-python3}"

# Package/report and route-policy gate. This does not prove live launch readiness.
"$PYTHON_BIN" bridge.py preflight
"$PYTHON_BIN" bridge.py verdict
# For a failing go/no-go exit code, use: "$PYTHON_BIN" bridge.py verdict --strict

if [ "$#" -eq 0 ]; then
  echo "usage: reports/openai_bridge_ci_gate.sh path/to/app-or-file [more paths...]" >&2
  exit 2
fi

"$PYTHON_BIN" bridge.py check "$@" --fail-on-boundary
