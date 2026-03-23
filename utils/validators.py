import re

STATUS_VALIDOS = ["Ativo", "Em Manutenção", "Inativo", "Reservado"]
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email.strip()))


def validar_senha(senha: str) -> tuple[bool, str]:
    senha = senha or ""

    if len(senha) < 8:
        return False, "A senha deve ter pelo menos 8 caracteres."

    if len(senha) > 128:
        return False, "A senha deve ter no máximo 128 caracteres."

    return True, ""


def validar_id_ativo(id_ativo: str) -> tuple[bool, str]:
    id_ativo = (id_ativo or "").strip()

    if not id_ativo:
        return False, "O ID do ativo não pode ficar vazio."

    if " " in id_ativo:
        return False, "O ID do ativo não pode conter espaços."

    if len(id_ativo) < 2:
        return False, "O ID do ativo deve ter pelo menos 2 caracteres."

    if len(id_ativo) > 20:
        return False, "O ID do ativo deve ter no máximo 20 caracteres."

    return True, ""


def validar_status(status: str) -> tuple[bool, str]:
    status = (status or "").strip()

    if not status:
        return False, "O status não pode ficar vazio."

    status_formatado = status.title()

    if status_formatado not in STATUS_VALIDOS:
        return False, f"Status inválido. Use um destes: {', '.join(STATUS_VALIDOS)}."

    return True, ""


def padronizar_texto(valor: str, modo: str = "title") -> str:
    valor = (valor or "").strip()

    if modo == "upper":
        return valor.upper()

    if modo == "strip":
        return valor

    return valor.title()