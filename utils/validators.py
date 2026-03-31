# utils/validators.py

# Módulo central de validações do sistema.
# Aqui ficam regras compartilhadas por:
# - autenticação
# - ativos
# - CLI
# - web

import re
from datetime import datetime

# Status válidos do domínio de ativos.
STATUS_VALIDOS = [
    "Disponível",
    "Em Uso",
    "Em Manutenção",
    "Reservado",
    "Baixado"
]

# Perfis válidos do sistema.
PERFIS_VALIDOS = [
    "usuario",
    "adm"
]

# Expressão regular básica para e-mail.
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_email(email: str) -> bool:
    """
    Valida formato básico de e-mail.
    """
    return bool(EMAIL_REGEX.match((email or "").strip()))


def validar_senha(senha: str) -> tuple[bool, str]:
    """
    Valida regras mínimas de senha.
    """
    senha = senha or ""

    if len(senha) < 8:
        return False, "A senha deve ter pelo menos 8 caracteres."

    if len(senha) > 128:
        return False, "A senha deve ter no máximo 128 caracteres."

    return True, ""


def validar_perfil(perfil: str) -> tuple[bool, str]:
    """
    Valida o perfil de acesso do usuário.
    """
    perfil = (perfil or "").strip().lower()

    if perfil not in PERFIS_VALIDOS:
        return False, f"Perfil inválido. Use um destes: {', '.join(PERFIS_VALIDOS)}."

    return True, ""


def validar_id_inteiro_positivo(valor, nome_campo: str) -> tuple[bool, str]:
    """
    Valida se um valor representa um inteiro positivo.
    """
    try:
        valor_int = int(valor)
    except (TypeError, ValueError):
        return False, f"O campo {nome_campo} deve ser um número inteiro válido."

    if valor_int <= 0:
        return False, f"O campo {nome_campo} deve ser maior que zero."

    return True, ""


def validar_id_ativo(id_ativo: str) -> tuple[bool, str]:
    """
    Valida o identificador do ativo.
    """
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
    """
    Valida se o status informado é permitido.
    """
    status = (status or "").strip().title()

    if not status:
        return False, "O status não pode ficar vazio."

    if status not in STATUS_VALIDOS:
        return False, f"Status inválido. Use um destes: {', '.join(STATUS_VALIDOS)}."

    return True, ""


def validar_texto_obrigatorio(
    valor: str,
    nome_campo: str,
    tamanho_maximo: int = 100
) -> tuple[bool, str]:
    """
    Valida campos textuais obrigatórios.
    """
    valor = (valor or "").strip()

    if not valor:
        return False, f"O campo {nome_campo} não pode ficar vazio."

    if len(valor) > tamanho_maximo:
        return False, f"O campo {nome_campo} deve ter no máximo {tamanho_maximo} caracteres."

    return True, ""


def validar_texto_opcional(
    valor: str | None,
    nome_campo: str,
    tamanho_maximo: int = 100
) -> tuple[bool, str]:
    """
    Valida campos textuais opcionais.
    """
    valor = (valor or "").strip()

    if not valor:
        return True, ""

    if len(valor) > tamanho_maximo:
        return False, f"O campo {nome_campo} deve ter no máximo {tamanho_maximo} caracteres."

    return True, ""


def padronizar_texto(valor: str | None, modo: str = "title") -> str:
    """
    Padroniza texto conforme o modo solicitado.
    """
    valor = (valor or "").strip()

    if modo == "upper":
        return valor.upper()

    if modo == "lower":
        return valor.lower()

    if modo == "strip":
        return valor

    return valor.title()


def validar_data_iso(data_str: str) -> tuple[bool, str]:
    """
    Valida data no formato YYYY-MM-DD.
    """
    data_str = (data_str or "").strip()

    if not data_str:
        return False, "A data não pode ficar vazia."

    try:
        datetime.strptime(data_str, "%Y-%m-%d")
        return True, ""
    except ValueError:
        return False, "Data inválida. Use o formato YYYY-MM-DD."


def validar_data_iso_opcional(data_str: str | None) -> tuple[bool, str]:
    """
    Valida data opcional no formato YYYY-MM-DD.
    """
    data_str = (data_str or "").strip()

    if not data_str:
        return True, ""

    return validar_data_iso(data_str)


def comparar_datas(data_inicial: str, data_final: str | None) -> tuple[bool, str]:
    """
    Garante que a data final não seja anterior à data inicial.
    """
    if not data_inicial or not data_final:
        return True, ""

    dt_inicial = datetime.strptime(data_inicial, "%Y-%m-%d")
    dt_final = datetime.strptime(data_final, "%Y-%m-%d")

    if dt_final < dt_inicial:
        return False, "A data final não pode ser anterior à data inicial."

    return True, ""


def validar_regras_ativo(
    status: str,
    usuario_responsavel: str | None,
    data_entrada: str,
    data_saida: str | None
) -> tuple[bool, str]:
    """
    Valida regras de negócio do ativo.
    """
    status_fmt = (status or "").strip().title()
    usuario_fmt = (usuario_responsavel or "").strip()
    data_saida_fmt = (data_saida or "").strip()

    ok, msg = validar_data_iso(data_entrada)
    if not ok:
        return False, msg

    ok, msg = validar_data_iso_opcional(data_saida_fmt)
    if not ok:
        return False, msg

    ok, msg = comparar_datas(data_entrada, data_saida_fmt)
    if not ok:
        return False, msg

    if status_fmt == "Baixado" and not data_saida_fmt:
        return False, "Ativos com status 'Baixado' devem possuir data de saída."

    if status_fmt == "Disponível" and data_saida_fmt:
        return False, "Ativos com status 'Disponível' não devem possuir data de saída."

    if status_fmt == "Em Uso" and not usuario_fmt:
        return False, "Ativos com status 'Em Uso' devem possuir responsável."

    return True, ""


def validar_ativo(ativo) -> None:
    """
    Valida o objeto Ativo completo.
    """
    ok, msg = validar_id_ativo(ativo.id_ativo)
    if not ok:
        raise ValueError(msg)

    for valor, nome in [
        (ativo.tipo, "tipo"),
        (ativo.marca, "marca"),
        (ativo.modelo, "modelo"),
        (ativo.departamento, "departamento"),
    ]:
        ok, msg = validar_texto_obrigatorio(valor, nome)
        if not ok:
            raise ValueError(msg)

    ok, msg = validar_texto_opcional(
        ativo.usuario_responsavel,
        "usuario_responsavel"
    )
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_status(ativo.status)
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_regras_ativo(
        ativo.status,
        ativo.usuario_responsavel,
        ativo.data_entrada,
        ativo.data_saida
    )
    if not ok:
        raise ValueError(msg)
    ok, msg = validar_texto_opcional(
        ativo.nota_fiscal,
        "nota_fiscal"
    )
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_texto_opcional(
        ativo.seguro,
        "seguro"
    )
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_documentacao_ativo(
        ativo.nota_fiscal,
        ativo.seguro
    )
    if not ok:
        raise ValueError(msg)
    
def validar_documentacao_ativo(
    nota_fiscal: str | None,
    seguro: str | None
) -> tuple[bool, str]:
    """
    Garante que pelo menos um dos campos
    nota_fiscal ou seguro esteja preenchido.
    """
    nota_fiscal_fmt = (nota_fiscal or "").strip()
    seguro_fmt = (seguro or "").strip()

    if not nota_fiscal_fmt and not seguro_fmt:
        return False, "É obrigatório informar pelo menos a nota fiscal ou o seguro do produto."

    return True, ""