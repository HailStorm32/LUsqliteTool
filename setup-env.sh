#!/usr/bin/env bash

set -euo pipefail

echo "Checking for Python virtual environment..."

if [[ ! -f ".env/bin/activate" ]]; then
    echo "Virtual environment not found. Creating one..."

    if command -v python3 >/dev/null 2>&1; then
        python3 -m venv .env
    elif command -v python >/dev/null 2>&1; then
        python -m venv .env
    else
        echo "Python was not found in PATH. Install Python 3 and retry." >&2
        exit 1
    fi
else
    echo "Virtual environment already exists."
fi

echo "Activating environment..."
# shellcheck disable=SC1091
source .env/bin/activate

VENV_PYTHON=".env/bin/python"

echo "Upgrading pip to the latest version..."
"${VENV_PYTHON}" -m pip install --upgrade pip

echo "Checking for requirements.txt..."
if [[ -f "requirements.txt" ]]; then
    echo "Installing packages from requirements.txt..."
    "${VENV_PYTHON}" -m pip install -r requirements.txt
else
    echo "No requirements.txt file found. Skipping package installation."
fi

echo "Python virtual environment is now active."
echo "setup complete"