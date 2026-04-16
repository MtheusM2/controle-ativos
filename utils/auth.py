"""
Helpers de autenticação para endpoints JSON/API.

Centraliza um decorator reutilizável (@require_auth_api()) para garantir que
rotas mutáveis validem sessão antes de validações complementares (ex.: CSRF).
"""

from __future__ import annotations

from functools import wraps

from flask import jsonify, session


def obter_user_id_autenticado() -> int | None:
    """
    Retorna o user_id autenticado da sessão, ou None quando não autenticado.
    """
    raw_user_id = session.get("user_id")
    if raw_user_id is None:
        return None

    # Mantém robustez para sessões legadas onde o id pode chegar como string.
    try:
        return int(raw_user_id)
    except (TypeError, ValueError):
        return None


def require_auth_api(*, mensagem: str = "Sessão expirada. Faça login novamente."):
    """
    Decorator para exigir autenticação em endpoints API/JSON.

    Retorna 401 padronizado quando não há sessão válida. Deve ser aplicado
    antes de @require_csrf() para preservar o contrato:
    - sem login: 401
    - com login e sem CSRF: 403
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = obter_user_id_autenticado()
            if user_id is None:
                # Mantém o contrato JSON já usado na camada web.
                return jsonify({"ok": False, "erro": mensagem}), 401

            # Injeta user_id no handler para evitar nova leitura de sessão.
            kwargs["user_id"] = user_id
            return func(*args, **kwargs)

        return wrapper

    return decorator
