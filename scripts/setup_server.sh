#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
fi

python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

mkdir -p logs web_app/static/uploads

echo "Setup concluido. Revise .env antes de iniciar o servico."