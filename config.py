"""
Configuração central da aplicação.

Este módulo é a fonte única de verdade para variáveis de ambiente e
carrega o arquivo .env da raiz do projeto com override=True para garantir
comportamento previsível em ambientes locais e scripts.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


# Diretório raiz do projeto (arquivo atual está na raiz).
BASE_DIR = Path(__file__).resolve().parent

# Caminho absoluto para o arquivo .env utilizado pela aplicação.
ENV_FILE = BASE_DIR / ".env"

# Carrega variáveis do .env e sobrescreve variáveis já existentes no processo.
# Isso evita inconsistência quando o terminal já possui variáveis antigas.
load_dotenv(dotenv_path=ENV_FILE, override=True)


def _get_required_str(name: str) -> str:
    """
    Obtém variável obrigatória do ambiente com validação explícita.

    Levanta ValueError com mensagem clara quando a variável está ausente
    ou vazia, sem exibir qualquer valor sensível em logs/erros.
    """
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ValueError(
            f"A variável obrigatória '{name}' não foi definida no ambiente/.env."
        )
    return value.strip()


def _get_port(name: str, default: int = 3306) -> int:
    """
    Obtém porta do ambiente com fallback seguro e validação numérica.
    """
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"A variável '{name}' deve ser um número inteiro.") from exc


# Configurações de banco de dados.
DB_HOST = os.getenv("DB_HOST", "localhost").strip()
DB_PORT = _get_port("DB_PORT", default=3306)
DB_USER = _get_required_str("DB_USER")
DB_PASSWORD = _get_required_str("DB_PASSWORD")
DB_NAME = _get_required_str("DB_NAME")

# Configurações de segurança da aplicação.
FLASK_SECRET_KEY = _get_required_str("FLASK_SECRET_KEY")
APP_PEPPER = _get_required_str("APP_PEPPER")
