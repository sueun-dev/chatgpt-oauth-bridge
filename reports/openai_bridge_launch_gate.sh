#!/usr/bin/env bash
set -euo pipefail
PYTHON_BIN="${PYTHON:-python3}"

# Live launch gate. Run from a normal local shell with network and localhost bind access.
"$PYTHON_BIN" bridge.py live-check "$@"
