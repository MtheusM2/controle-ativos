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
