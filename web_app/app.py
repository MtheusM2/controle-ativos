from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from config import (  # noqa: E402
    FLASK_DEBUG,
    FLASK_SECRET_KEY,
    LOG_DIR,
    LOG_LEVEL,
    SESSION_COOKIE_SECURE,
    SESSION_LIFETIME_MINUTES,
    STORAGE_TYPE,
    S3_BUCKET,
    S3_REGION,
    S3_ACCESS_KEY_ID,
    S3_SECRET_ACCESS_KEY,
    S3_ENDPOINT_URL,
    IS_PRODUCTION,
    PROXY_FIX_ENABLED,
    PROXY_FIX_X_FOR,
    PROXY_FIX_X_PROTO,
    PROXY_FIX_X_HOST,
    PREFERRED_URL_SCHEME,
    SERVER_NAME,
    validar_producao,
)
from services.ativos_arquivo_service import AtivosArquivoService  # noqa: E402
from services.ativos_service import AtivosService  # noqa: E402
from services.auth_service import AuthService  # noqa: E402
from services.empresa_service import EmpresaService  # noqa: E402
from services.storage_backend import (  # noqa: E402
    LocalStorageBackend,
    S3StorageBackend,
    StorageBackendError,
)
from utils.csrf import gerar_token_csrf  # noqa: E402
from utils.logging_config import configurar_logging  # noqa: E402
from web_app.routes.ativos_routes import registrar_rotas_ativos  # noqa: E402
from web_app.routes.auth_routes import registrar_rotas_auth  # noqa: E402


def create_app(
    config_overrides: dict | None = None,
    service_overrides: dict | None = None,
) -> Flask:
    """
    Cria a aplicacao Flask principal com suporte a testes e injecao de services.

    Valida configuracao de seguranca se estiver em producao.
    """
    # Valida que producao atende requisitos de seguranca.
    validar_producao()

    flask_app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )

    flask_app.config.update(
        SECRET_KEY=FLASK_SECRET_KEY,
        # SESSION_COOKIE_HTTPONLY: Cookie nao acessivel por JavaScript (previne XSS).
        # Sempre True em todos os ambientes.
        SESSION_COOKIE_HTTPONLY=True,
        # SESSION_COOKIE_SAMESITE: Previne CSRF simples. "Lax" permite requisicoes
        # de navegacao normal mas bloqueia POST cross-site.
        SESSION_COOKIE_SAMESITE="Lax",
        # SESSION_COOKIE_SECURE: Cookie enviado apenas em HTTPS.
        # Desenvolvimento: False (HTTP local)
        # Producao: True (obrigatorio quando HTTPS ativo via proxy reverso)
        # Controlado por variavel SESSION_COOKIE_SECURE em config.py
        # Nota: Com PROXY_FIX_ENABLED=1, request.is_secure reflete X-Forwarded-Proto correto
        SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=SESSION_LIFETIME_MINUTES),
        JSON_AS_ASCII=False,
        TEMPLATES_AUTO_RELOAD=FLASK_DEBUG,
        UPLOAD_FOLDER=str(BASE_DIR / "static" / "uploads"),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
        BASE_DIR=str(BASE_DIR),
        # PREFERRED_URL_SCHEME: Scheme usado por url_for() e redirecionamentos.
        # Essencial em produção atrás de proxy reverso HTTPS (Cloudflare Tunnel, etc.)
        # Com ProxyFix ativo, request.is_secure reflete HTTPS via X-Forwarded-Proto,
        # mas Flask ainda precisa desta configuração para url_for() gerar URLs HTTPS.
        PREFERRED_URL_SCHEME=PREFERRED_URL_SCHEME,
        # SERVER_NAME: Hostname para validacoes e redirecionamentos do Flask.
        # Deixar None em desenvolvimento. Em produção com Tunnel, configure com dominio publico.
        # Exemplo: "sistema.empresa.com"
        SERVER_NAME=SERVER_NAME,
    )

    if config_overrides:
        flask_app.config.update(config_overrides)

    # Cria diretório de logs se necessário.
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    # Se usar storage local, cria diretório de uploads (não é usado em S3).
    # Em Render, este diretório será ephemeral e não será persistido.
    if STORAGE_TYPE == "local":
        Path(flask_app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    configurar_logging(flask_app, level_name=LOG_LEVEL, log_dir=LOG_DIR)

    # Disponibiliza gerar_token_csrf() em todos os templates Jinja sem importação explícita.
    flask_app.jinja_env.globals["csrf_token"] = gerar_token_csrf

    # Instancia o backend de armazenamento correto.
    if STORAGE_TYPE == "s3":
        flask_app.logger.info("Inicializando backend S3 para armazenamento de arquivos.")
        try:
            storage_backend = S3StorageBackend(
                bucket_name=S3_BUCKET,
                region=S3_REGION,
                access_key_id=S3_ACCESS_KEY_ID,
                secret_access_key=S3_SECRET_ACCESS_KEY,
                endpoint_url=S3_ENDPOINT_URL,
            )
        except StorageBackendError as e:
            flask_app.logger.error(f"Falha ao inicializar S3: {e}")
            raise
    else:
        flask_app.logger.info("Inicializando backend local para armazenamento de arquivos.")
        storage_backend = LocalStorageBackend(
            base_dir=flask_app.config["UPLOAD_FOLDER"]
        )

    services = service_overrides or {}
    auth_service = services.get("auth_service") or AuthService()
    ativos_service = services.get("ativos_service") or AtivosService()
    empresa_service = services.get("empresa_service") or EmpresaService()
    ativos_arquivo_service = services.get("ativos_arquivo_service") or AtivosArquivoService(
        storage_backend=storage_backend
    )

    registrar_rotas_auth(
        flask_app,
        auth_service=auth_service,
        empresa_service=empresa_service,
    )
    registrar_rotas_ativos(
        flask_app,
        ativos_service=ativos_service,
        ativos_arquivo_service=ativos_arquivo_service,
    )

    @flask_app.get("/health")
    def health():
        """
        Endpoint simples para smoke test e monitoramento local.
        """
        return jsonify({"ok": True, "status": "healthy"})

    @flask_app.get("/config-diagnostico")
    def config_diagnostico():
        """
        Endpoint de diagnostico para validar configuracao pos-deploy.

        Em producao, restrito a requisições locais (127.0.0.1, ::1) para evitar
        exposição de configuração via acesso público (ex.: Cloudflare Tunnel).

        Em desenvolvimento, acessível de qualquer origem.
        """
        from config import diagnosticar_config, IS_PRODUCTION

        # Em produção, rejeita requisições de fora do servidor local.
        # Com ProxyFix ativo, request.remote_addr é o IP real do cliente.
        # Requisições via Cloudflare Tunnel terão IP de cliente externo → bloqueadas.
        if IS_PRODUCTION and request.remote_addr not in ("127.0.0.1", "::1"):
            return jsonify({"ok": False, "erro": "Acesso restrito a localhost."}), 403

        diag = diagnosticar_config()

        # Em producao, alertar se .env foi carregado (nao deve acontecer).
        alertas = []
        if IS_PRODUCTION and diag.get("env_file_carregado"):
            alertas.append("AVISO: .env foi carregado em ambiente de producao.")

        return jsonify({
            "ok": True,
            "is_production": IS_PRODUCTION,
            "diagnostico": diag,
            "alertas": alertas,
        })

    @flask_app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        """
        Evita que o Flask devolva HTML bruto nas rotas de backend.
        """
        if request.method != "GET" or request.path.startswith(("/ativos", "/anexos")) or request.path in {
            "/login",
            "/register",
            "/logout",
            "/forgot-password",
            "/session",
            "/health",
        }:
            return jsonify({"ok": False, "erro": error.description}), error.code

        return error

    @flask_app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        """
        Padroniza falhas inesperadas em produção e repropaga em debug/testing.
        """
        flask_app.logger.exception("Erro interno nao tratado: %s", error)

        # Em desenvolvimento, deixa o traceback subir para o depurador do Flask.
        if flask_app.debug or flask_app.testing:
            raise error

        return jsonify({"ok": False, "erro": "Erro interno do servidor."}), 500

    # Aplica middleware de proxy reverso quando necessário.
    # Cloudflare Tunnel, IIS, Nginx e outros proxies encaminham headers como X-Forwarded-For,
    # X-Forwarded-Proto, etc. Sem o ProxyFix:
    # - request.remote_addr retorna o IP do proxy (127.0.0.1, não o cliente real)
    # - request.is_secure retorna False (conexão proxy é HTTP)
    # - SESSION_COOKIE_SECURE=1 quebra porque Flask vê HTTP não HTTPS
    if PROXY_FIX_ENABLED:
        from werkzeug.middleware.proxy_fix import ProxyFix
        flask_app.wsgi_app = ProxyFix(
            flask_app.wsgi_app,
            x_for=PROXY_FIX_X_FOR,
            x_proto=PROXY_FIX_X_PROTO,
            x_host=PROXY_FIX_X_HOST,
            x_prefix=0,
        )
        flask_app.logger.info(
            "ProxyFix ativado: x_for=%d, x_proto=%d, x_host=%d. "
            "request.remote_addr e request.is_secure sao agora derivados de headers de proxy.",
            PROXY_FIX_X_FOR, PROXY_FIX_X_PROTO, PROXY_FIX_X_HOST,
        )

    flask_app.logger.info("Aplicacao Flask inicializada com sucesso.")
    return flask_app


application = create_app()


if __name__ == "__main__":
    # O modo debug é controlado pela configuração centralizada para evitar drift entre entrypoints.
    application.run(debug=FLASK_DEBUG)
