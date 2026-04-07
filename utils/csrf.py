"""
Proteção CSRF simples baseada em itsdangerous.

Gera tokens assinados vinculados à sessão do usuário e válidos por
SESSION_LIFETIME_MINUTES. Compatível com formulários tradicionais (hidden input).
"""

from __future__ import annotations

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
