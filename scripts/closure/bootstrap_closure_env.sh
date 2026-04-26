#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv-closure}"

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip wheel setuptools
pip install -r "$ROOT_DIR/backend/requirements.txt"
if [ -f "$ROOT_DIR/backend/requirements-dev.txt" ]; then
  pip install -r "$ROOT_DIR/backend/requirements-dev.txt"
fi
if [ -d "$ROOT_DIR/frontend" ]; then
  pushd "$ROOT_DIR/frontend" >/dev/null
  npm ci
  popd >/dev/null
fi

echo "Closure environment ready at: $VENV_DIR"
echo "Activate with: source $VENV_DIR/bin/activate"
