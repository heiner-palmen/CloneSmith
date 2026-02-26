#!/usr/bin/env bash
set -euo pipefail

# Creates a virtual environment in ./venv and installs requirements.txt
# Usage: ./setup_venv.sh
# Optional env vars: PYTHON (defaults to python3), VENV_DIR (defaults to venv)

PYTHON=${PYTHON:-python3}
VENV_DIR=${VENV_DIR:-venv}

echo "Creating virtual environment in ${VENV_DIR} using ${PYTHON}..."
${PYTHON} -m venv "${VENV_DIR}"

echo "Upgrading pip and installing requirements..."
"${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel

if [ -f requirements.txt ]; then
  "${VENV_DIR}/bin/pip" install -r requirements.txt
else
  echo "requirements.txt not found in $(pwd)" >&2
  exit 1
fi

echo
echo "Done. To activate the venv run: source ${VENV_DIR}/bin/activate"
