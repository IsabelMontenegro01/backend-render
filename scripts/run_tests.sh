#!/usr/bin/env bash
set -euo pipefail

# Ativa venv (se existir) e executa pytest desabilitando autoload de plugins
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  . .venv/bin/activate
fi

# Ensure package import path points to `backend/` so tests can import `app` package
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/backend"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
pytest -q backend/tests "$@"
