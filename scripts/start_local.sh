#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ ! -x .venv/bin/python ]; then
    echo "Virtualenv ausente. Execute scripts/setup_server.sh primeiro."
    exit 1
fi

export FLASK_DEBUG=1
export FLASK_RUN_HOST=127.0.0.1
export FLASK_RUN_PORT=5000
./.venv/bin/python app.py