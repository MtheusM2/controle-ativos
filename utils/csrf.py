"""
Proteção CSRF simples baseada em itsdangerous.

Gera tokens assinados vinculados à sessão do usuário e válidos por
SESSION_LIFETIME_MINUTES. Compatível com formulários tradicionais (hidden input).

Fornece um decorator reutilizável (@require_csrf()) que encapsula a validação
de token CSRF para endpoints mutáveis (POST, PUT, DELETE, PATCH).
"""

from __future__ import annotations

from functools import wraps
from flask import Request, jsonify
from flask import current_app, session
from itsdangerous import BadData, URLSafeTimedSerializer


def _serializer() -> URLSafeTimedSerializer:
    """
    Retorna o serializador configurado com a chave secreta da aplicação.
    """
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="csrf")


def _csrf_identity() -> str:
    """
    Deriva a identidade CSRF do usuário a partir da sessão atual.
    Usuários não autenticados recebem a sessão como identidade.
    """
    user_id = session.get("user_id")
    if user_id is not None:
        return f"user:{user_id}"
    # Usa o sid da sessão Flask como âncora para usuários anônimos (ex.: login, cadastro).
    return f"anon:{session.get('_id', 'unknown')}"


def gerar_token_csrf() -> str:
    """
    Gera um token CSRF assinado e vinculado à sessão atual.
    """
    return _serializer().dumps(_csrf_identity())


def validar_token_csrf(token: str | None, *, max_age_seconds: int = 7200) -> bool:
    """
    Valida o token CSRF recebido no formulário.

    Retorna False se o token estiver ausente, adulterado ou expirado.
    """
    if not token:
        return False

    try:
        identidade = _serializer().loads(token, max_age=max_age_seconds)
    except BadData:
        return False

    return identidade == _csrf_identity()


def obter_token_csrf_da_requisicao(request: Request) -> str | None:
    """
    Extrai o token CSRF da requisição seguindo prioridade consistente.

    Ordem de leitura:
    1) Header X-CSRF-Token (fluxo fetch)
    2) Campo csrf_token no formulário (multipart/form-data e x-www-form-urlencoded)
    3) Campo csrf_token no JSON (fallback para clientes sem header)
    """
    token_header = (request.headers.get("X-CSRF-Token") or "").strip()
    if token_header:
        return token_header

    token_form = (request.form.get("csrf_token") or "").strip()
    if token_form:
        return token_form

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        token_json = str(payload.get("csrf_token") or "").strip()
        if token_json:
            return token_json

    return None


def validar_csrf_da_requisicao(request: Request, *, max_age_seconds: int = 7200) -> bool:
    """
    Valida CSRF de forma padronizada para qualquer tipo de payload HTTP.
    """
    token = obter_token_csrf_da_requisicao(request)
    return validar_token_csrf(token, max_age_seconds=max_age_seconds)


def require_csrf(*, max_age_seconds: int = 7200):
    """
    Decorator reutilizável que encapsula validação CSRF para endpoints mutáveis.

    Protege rotas POST, PUT, DELETE e PATCH contra ataques CSRF validando
    o token conforme ordem de prioridade:
    1) Header X-CSRF-Token (fluxo fetch moderno)
    2) Campo csrf_token em form-data (formulários tradicionais, multipart)
    3) Campo csrf_token em JSON (fallback para clientes sem header)

    Rejeita com resposta JSON 403 se o token estiver ausente, inválido ou expirado.

    Uso:
        @app.post("/ativos")
        @require_csrf()
        def criar_ativo():
            ...

    Notas de implementação:
    - O decorator deve ser aplicado ANTES dos decorators de rota do Flask
      (@app.post, @app.put, etc.) para que a validação ocorra antes do
      handler da rota ser executado.
    - Retorna um erro JSON padronizado {"ok": False, "erro": "..."}
      com status HTTP 403, mantendo consistência com outras validações
      de segurança na camada web.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request as flask_request

            if not validar_csrf_da_requisicao(flask_request, max_age_seconds=max_age_seconds):
                # Respostas padronizadas de erro CSRF mantêm formato JSON consistente.
                # Essa resposta reflete a mesma formatação usada em _json_error nas rotas.
                return jsonify({
                    "ok": False,
                    "erro": "Requisição inválida. Atualize a página e tente novamente.",
                }), 403

            return func(*args, **kwargs)

        return wrapper

    return decorator
