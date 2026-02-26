#!/bin/bash

# Resolve the directory containing this script and run the local Python file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/timemeasureWayland.py"

if [[ ! -f "$SCRIPT_PATH" ]]; then
    echo "Error: Python script not found at $SCRIPT_PATH"
    exit 1
fi

python3 "$SCRIPT_PATH"
rc=$?
if [[ $rc -ne 0 ]]; then
    echo "Error: timemeasureWayland.py failed (exit $rc)"
    exit $rc
fi
