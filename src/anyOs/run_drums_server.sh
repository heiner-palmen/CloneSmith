#!/bin/bash

# Resolve the directory containing this script and run the local Python file (prefer venv)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/drums_server.py"
VENV_DIR="${VENV_DIR:-venv}"
VENV_PY="$SCRIPT_DIR/$VENV_DIR/bin/python"

if [[ ! -f "$SCRIPT_PATH" ]]; then
    echo "Error: Python script not found at $SCRIPT_PATH"
    exit 1
fi

if [[ -x "$VENV_PY" ]]; then
    echo "Using virtualenv python: $VENV_PY"
    "$VENV_PY" "$SCRIPT_PATH"
else
    echo "Virtualenv not found at $VENV_PY; falling back to system python3"
    python3 "$SCRIPT_PATH"
fi

rc=$?
if [[ $rc -ne 0 ]]; then
    echo "Error: drums_server.py failed (exit $rc)"
    exit $rc
fi
