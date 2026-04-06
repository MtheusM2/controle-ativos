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
)
from services.ativos_arquivo_service import AtivosArquivoService  # noqa: E402
from services.ativos_service import AtivosService  # noqa: E402
from services.auth_service import AuthService  # noqa: E402
from services.empresa_service import EmpresaService  # noqa: E402
from utils.logging_config import configure_logging  # noqa: E402
from web_app.routes.ativos_routes import registrar_rotas_ativos  # noqa: E402
from web_app.routes.auth_routes import registrar_rotas_auth  # noqa: E402


def create_app(
    config_overrides: dict | None = None,
    service_overrides: dict | None = None,
) -> Flask:
    """
    Cria a aplicacao Flask principal com suporte a testes e injecao de services.
    """
    flask_app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )

    flask_app.config.update(
        SECRET_KEY=FLASK_SECRET_KEY,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=SESSION_LIFETIME_MINUTES),
        JSON_AS_ASCII=False,
        TEMPLATES_AUTO_RELOAD=FLASK_DEBUG,
        UPLOAD_FOLDER=str(BASE_DIR / "static" / "uploads"),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
        BASE_DIR=str(BASE_DIR),
    )

    if config_overrides:
        flask_app.config.update(config_overrides)

    # Garante que os diretórios operacionais existam antes do primeiro request.
    Path(flask_app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    configure_logging(flask_app, level_name=LOG_LEVEL, log_dir=LOG_DIR)

    services = service_overrides or {}
    auth_service = services.get("auth_service") or AuthService()
    ativos_service = services.get("ativos_service") or AtivosService()
    empresa_service = services.get("empresa_service") or EmpresaService()
    ativos_arquivo_service = services.get("ativos_arquivo_service") or AtivosArquivoService(
        upload_base_dir=flask_app.config["UPLOAD_FOLDER"]
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

    flask_app.logger.info("Aplicacao Flask inicializada com sucesso.")
    return flask_app


application = create_app()


if __name__ == "__main__":
    # O modo debug é controlado pela configuração centralizada para evitar drift entre entrypoints.
    application.run(debug=FLASK_DEBUG)
