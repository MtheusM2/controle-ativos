"""
Configuracao central da aplicacao.

Este modulo concentra a leitura das variaveis de ambiente consumidas por:
- banco de dados
- seguranca
- sessao Flask
- logging

Estrategia de secrets:
- Desenvolvimento: Carrega .env como fallback para facilitar execucao local.
- Producao: Usa APENAS variaveis de ambiente do SO. .env e ignorado.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# Detecta se estamos em producao.
# Prioridade: ENVIRONMENT > HTTPS > presenca de SO env vars secretos
ENVIRONMENT = os.getenv("ENVIRONMENT", "").strip().lower()
IS_PRODUCTION = (
    ENVIRONMENT == "production" or
    os.getenv("HTTPS", "").lower() == "on" or
    (os.getenv("DB_PASSWORD") is not None and ENVIRONMENT != "development")
)

# Em desenvolvimento, carrega .env como fallback.
# Em producao, ignora .env e exige variaveis de ambiente do SO.
if not IS_PRODUCTION:
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

# Proxy reverso confiável (Cloudflare Tunnel, IIS, Nginx, etc.).
# Ativar (=1) apenas quando há um proxy na frente do Waitress que encaminha headers de proxy.
# Controla o middleware ProxyFix do Werkzeug que reconstitui IP real e protocolo HTTPS.
PROXY_FIX_ENABLED = os.getenv("PROXY_FIX_ENABLED", "0").strip() == "1"
# Número de proxies que adicionam X-Forwarded-For (Cloudflare Tunnel: 1, IIS+Tunnel: 2)
PROXY_FIX_X_FOR = _get_int("PROXY_FIX_X_FOR", 1)
# Número de proxies que adicionam X-Forwarded-Proto
PROXY_FIX_X_PROTO = _get_int("PROXY_FIX_X_PROTO", 1)
# Número de proxies que adicionam X-Forwarded-Host (0 = desabilitar; geralmente não confiável)
PROXY_FIX_X_HOST = _get_int("PROXY_FIX_X_HOST", 0)

# Scheme (http/https) que Flask usa para gerar URLs via url_for() e redirecionamentos.
# Em desenvolvimento (HTTP local): "http"
# Em produção com Cloudflare Tunnel (HTTPS): "https"
# Padrão automático: "https" em produção, "http" em desenvolvimento.
PREFERRED_URL_SCHEME = os.getenv("PREFERRED_URL_SCHEME", "https" if IS_PRODUCTION else "http").strip()

# Hostname para validações e redirecionamentos do Flask (ex: "sistema.empresa.com").
# Deixar vazio/None para desenvolvimento local (Flask não força validação de host).
# Em produção com Cloudflare Tunnel, configure com o domínio público.
SERVER_NAME = os.getenv("SERVER_NAME", "").strip() or None

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


def diagnosticar_config() -> dict:
    """
    Diagnostica e documenta a origem de cada variavel de configuracao.

    Retorno: dict com informacoes sobre como cada variavel foi carregada.
    Uso: chamado no startup para validacao.
    """
    return {
        "is_production": IS_PRODUCTION,
        "environment": ENVIRONMENT,
        "env_file_carregado": not IS_PRODUCTION,
        "db_host": DB_HOST,
        "db_user": DB_USER,
        "db_name": DB_NAME,
        "flask_debug": FLASK_DEBUG,
        "session_cookie_secure": SESSION_COOKIE_SECURE,
        "preferred_url_scheme": PREFERRED_URL_SCHEME,
        "server_name": SERVER_NAME,
        "log_level": LOG_LEVEL,
        "log_dir": LOG_DIR,
        "storage_type": STORAGE_TYPE,
        "proxy_fix_enabled": PROXY_FIX_ENABLED,
        "proxy_fix_x_for": PROXY_FIX_X_FOR,
        "proxy_fix_x_proto": PROXY_FIX_X_PROTO,
        "proxy_fix_x_host": PROXY_FIX_X_HOST,
    }


def validar_producao():
    """
    Valida que configuracao de producao atenda requisitos de seguranca.

    Levanta ValueError se algum requisito critico nao for atendido.
    Chamado no startup em producao.
    """
    if not IS_PRODUCTION:
        return  # Nao validar em desenvolvimento

    # Em producao, HTTPS deve estar ativo ou em teste.
    # Se nao estiver, logar aviso (nao eh obrigatorio no startup,
    # mas sera obrigatorio ao fazer deploy real).

    # Verificar que secrets sensveis nao sao valores placeholder.
    if FLASK_SECRET_KEY in ("CHANGE_ME", "", "dev"):
        raise ValueError(
            "Em producao, FLASK_SECRET_KEY nao pode ser placeholder. "
            "Defina uma chave segura em variavel de ambiente."
        )

    if APP_PEPPER in ("CHANGE_ME", "", "dev"):
        raise ValueError(
            "Em producao, APP_PEPPER nao pode ser placeholder. "
            "Defina um pepper seguro em variavel de ambiente."
        )

    if DB_PASSWORD in ("CHANGE_ME", "", "dev"):
        raise ValueError(
            "Em producao, DB_PASSWORD nao pode ser placeholder. "
            "Defina a senha do banco em variavel de ambiente."
        )

    # Validar que .env nao esta sendo carregado em producao.
    # (config.py ja garante isso, mas verificar para seguranca)
    if IS_PRODUCTION and ENV_FILE.exists():
        import logging
        logging.warning(
            "Arquivo .env existe em ambiente de producao. "
            "Verifique se as variaveis estao sendo carregadas do SO, nao do .env."
        )
