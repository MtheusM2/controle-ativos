#!/usr/bin/env bash
# setup_server.sh — Bootstrap completo para novo servidor Linux
# Uso: bash scripts/setup_server.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "=== Controle de Ativos — Setup de Servidor ==="

# ─────────────────────────────────────────────────
# 1. Variáveis de ambiente
# ─────────────────────────────────────────────────
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[ATENÇÃO] .env criado a partir do .env.example."
        echo "          Configure as variáveis antes de continuar."
    else
        echo "[ERRO] Arquivo .env.example não encontrado."
        exit 1
    fi
fi

# ─────────────────────────────────────────────────
# 2. Ambiente virtual Python
# ─────────────────────────────────────────────────
if [ ! -d .venv ]; then
    python3 -m venv .venv
    echo "[OK] Ambiente virtual criado."
fi

./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt
echo "[OK] Dependências instaladas."

# ─────────────────────────────────────────────────
# 3. Diretórios operacionais
# ─────────────────────────────────────────────────
mkdir -p logs
mkdir -p web_app/static/uploads/ativos

# Permissões restritivas: apenas o usuário da aplicação pode ler uploads.
chmod 750 web_app/static/uploads
chmod 750 web_app/static/uploads/ativos
echo "[OK] Diretórios criados com permissões restritivas."

# ─────────────────────────────────────────────────
# 4. Diagnóstico de configuração
# ─────────────────────────────────────────────────
echo "[INFO] Verificando configuração de runtime..."
python3 scripts/diagnose_runtime_config.py || true

# ─────────────────────────────────────────────────
# 5. Resumo
# ─────────────────────────────────────────────────
echo ""
echo "=== Setup concluído ==="
echo "Próximos passos:"
echo "  1. Edite .env com as credenciais reais do banco e da aplicação"
echo "  2. Aplique as migrações de banco: mysql -u root -p < database/schema.sql"
echo "  3. Configure o serviço: sudo cp deploy/systemd/controle_ativos.service /etc/systemd/system/"
echo "  4. Configure o Nginx: sudo cp deploy/nginx/controle_ativos.conf /etc/nginx/sites-available/"
echo "  5. Ative e inicie: sudo systemctl enable --now controle_ativos"
echo "  6. Verifique: curl http://localhost:8000/health"
