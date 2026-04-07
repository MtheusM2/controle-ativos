"""
Configuracao central da aplicacao.

Este modulo concentra a leitura das variaveis de ambiente consumidas por:
- banco de dados
- seguranca
- sessao Flask
- logging
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# Carrega variaveis locais de ambiente para manter comportamento previsivel
# ao executar scripts, testes e a aplicacao Flask.
load_dotenv(dotenv_path=ENV_FILE, override=True)


def _get_required_str(name: str) -> str:
    """
    Obtem variavel obrigatoria do ambiente com validacao explicita.
    """
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ValueError(
            f"A variavel obrigatoria '{name}' nao foi definida no ambiente/.env."
        )
    return value.strip()


def _get_int(name: str, default: int) -> int:
    """
    Obtem inteiro do ambiente com fallback validado.
    """
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"A variavel '{name}' deve ser um numero inteiro.") from exc


DB_HOST = os.getenv("DB_HOST", "localhost").strip()
DB_PORT = _get_int("DB_PORT", 3306)
DB_USER = _get_required_str("DB_USER")
DB_PASSWORD = _get_required_str("DB_PASSWORD")
DB_NAME = _get_required_str("DB_NAME")

FLASK_SECRET_KEY = _get_required_str("FLASK_SECRET_KEY")
APP_PEPPER = _get_required_str("APP_PEPPER")

FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0").strip() == "1"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0").strip() == "1"
SESSION_LIFETIME_MINUTES = _get_int("SESSION_LIFETIME_MINUTES", 120)

AUTH_MAX_FAILED_ATTEMPTS = _get_int("AUTH_MAX_FAILED_ATTEMPTS", 5)
AUTH_LOCKOUT_MINUTES = _get_int("AUTH_LOCKOUT_MINUTES", 15)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"
LOG_DIR = os.getenv("LOG_DIR", str(BASE_DIR / "logs")).strip()

# Configuração de armazenamento de arquivos.
# STORAGE_TYPE: "local" (padrão, para Windows/desenvolvimento) ou "s3" (para Render/cloud).
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local").strip().lower()

# Parâmetros de S3 (usados apenas se STORAGE_TYPE="s3").
S3_BUCKET = os.getenv("S3_BUCKET", "").strip()
S3_REGION = os.getenv("S3_REGION", "us-east-1").strip()
S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID", "").strip()
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY", "").strip()
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "").strip() or None

# Validação: se STORAGE_TYPE="s3", bucket deve estar definido.
if STORAGE_TYPE == "s3" and not S3_BUCKET:
    raise ValueError(
        "Se STORAGE_TYPE='s3', a variavel obrigatoria 'S3_BUCKET' deve ser definida."
    )

# Timeout para conexão com banco de dados (em segundos).
# Render pode ter latência inicial maior; aumentar se necessário.
DB_CONNECTION_TIMEOUT = _get_int("DB_CONNECTION_TIMEOUT", 30)
