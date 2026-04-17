# utils/validators.py

# Módulo central de validações do sistema.
# Aqui ficam regras compartilhadas por:
# - autenticação
# - ativos
# - CLI
# - web

import re
from datetime import date, datetime

STATUS_VALIDOS = [
    "Disponível",
    "Em Uso",
    "Em Manutenção",
    "Reservado",
    "Baixado"
]

# Lista oficial dos tipos permitidos no cadastro inteligente.
TIPOS_ATIVO_VALIDOS = [
    "Notebook",
    "Desktop",
    "Celular",
    "Monitor",
    "Mouse",
    "Teclado",
    "Headset",
    "Adaptador",
    "Cabo",
    "Carregador",
    "Outro",
]

SETORES_VALIDOS = [
    "T.I",
    "RH",
    "ADM",
    "Financeiro",
    "Vendas",
    "Marketing",
    "Infraestrutura",
    "Apoio",
    "Estagiários",
    "Diretoria",
    "Manutenção",
    "Técnica",
    "Logística",
    "Licitação",
]

CONDICOES_VALIDAS = [
    "Novo",
    "Bom",
    "Regular",
    "Ruim",
    "Inativo",
]

# Fase 3 Round 2.1: Unidades oficiais padronizadas
UNIDADES_VALIDAS = [
    "Opus Medical",
    "Vicente Martins",
]

PERFIS_VALIDOS = [
    "usuario",
    # Mantem compatibilidade com legado (adm) e novo rotulo (admin).
    "adm",
    "admin"
]

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CODIGO_INTERNO_REGEX = re.compile(r"^[A-Z0-9._/-]+$")
SERIAL_REGEX = re.compile(r"^[A-Z0-9._/-]+$")


def _somente_digitos(valor: str | None) -> str:
    """
    Remove qualquer caractere não numérico para normalização de campos telefônicos.
    """
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def normalizar_numero_linha(numero_linha: str | None) -> str | None:
    """
    Normaliza número de linha para apenas dígitos, preservando compatibilidade com DDI opcional.
    """
    digitos = _somente_digitos(numero_linha)
    return digitos or None


def validar_numero_linha(numero_linha: str | None) -> tuple[bool, str]:
    """
    Valida número de linha/chip.

    Aceita:
    - 10 ou 11 dígitos (DDD + número nacional)
    - 12 ou 13 dígitos iniciando com 55 (com DDI do Brasil)
    """
    digitos = _somente_digitos(numero_linha)
    if not digitos:
        return True, ""

    tamanho = len(digitos)
    if tamanho in {10, 11}:
        return True, ""

    if tamanho in {12, 13} and digitos.startswith("55"):
        return True, ""

    return False, (
        "O campo numero_linha deve conter 10 ou 11 dígitos "
        "(ou 12/13 com DDI 55)."
    )


# Removido em Fase 3 Round 3: funções de normalização e validação de IMEI
# normalizar_imei(), _luhn_valido(), validar_imei() — não mais necessárias no fluxo de celular


def validar_teamviewer_id(teamviewer_id: str | None) -> tuple[bool, str]:
    """
    Valida identificador do TeamViewer para acesso remoto.

    Regras:
    - Campo opcional (vazio é permitido)
    - Se fornecido: máximo 100 caracteres
    - Aceita apenas identificadores plausíveis: alfanuméricos, hífen, sublinhado
    - Rejeita padrões que parecem credencial (caracteres especiais demais)

    Exemplos válidos:
    - "123456789" (numérico típico do TeamViewer)
    - "ABC-123-DEF" (com hífens)
    - "team_viewer_123" (com sublinhado)

    Exemplos inválidos:
    - "pass@123!secure" (caracteres especiais de senha)
    - "!@#$%^&*()" (apenas caracteres especiais)
    - Vazio é OK (campo opcional)
    """
    teamviewer_id = (teamviewer_id or "").strip()

    # Campo opcional — permite vazio
    if not teamviewer_id:
        return True, ""

    # Limite de tamanho razoável (campo VARCHAR(100) no BD)
    if len(teamviewer_id) > 100:
        return False, "O identificador TeamViewer não pode exceder 100 caracteres."

    # Rejeitar padrões que parecem credencial (muitos caracteres especiais)
    caracteres_especiais = sum(1 for c in teamviewer_id if not c.isalnum() and c not in "-_")
    if caracteres_especiais > 3:
        return (
            False,
            "O identificador TeamViewer contém muitos caracteres especiais. "
            "Não importar credenciais sensíveis em texto puro."
        )

    # Permitir apenas alfanuméricos, hífen e sublinhado
    # Rejeitar símbolos típicos de senha como @, !, $, etc.
    caracteres_proibidos = set("!@#$%^&*()[]{}/<>\\|:;\"'")
    if any(c in caracteres_proibidos for c in teamviewer_id):
        return (
            False,
            "O identificador TeamViewer contém caracteres inválidos. "
            "Use apenas letras, números, hífen e sublinhado."
        )

    return True, ""


def validar_anydesk_id(anydesk_id: str | None) -> tuple[bool, str]:
    """
    Valida identificador do AnyDesk para acesso remoto.

    Regras:
    - Campo opcional (vazio é permitido)
    - Se fornecido: máximo 100 caracteres
    - Aceita apenas identificadores plausíveis: alfanuméricos, hífen
    - Rejeita padrões que parecem credencial (caracteres especiais demais)

    Exemplos válidos:
    - "123456789012345" (numérico típico do AnyDesk)
    - "ABC-123-DEF-GHI" (com hífens)

    Exemplos inválidos:
    - "pass@123!secure" (caracteres especiais de senha)
    - "!@#$%^&*()" (apenas caracteres especiais)
    - Vazio é OK (campo opcional)
    """
    anydesk_id = (anydesk_id or "").strip()

    # Campo opcional — permite vazio
    if not anydesk_id:
        return True, ""

    # Limite de tamanho razoável (campo VARCHAR(100) no BD)
    if len(anydesk_id) > 100:
        return False, "O identificador AnyDesk não pode exceder 100 caracteres."

    # Rejeitar padrões que parecem credencial (muitos caracteres especiais)
    caracteres_especiais = sum(1 for c in anydesk_id if not c.isalnum() and c != "-")
    if caracteres_especiais > 2:
        return (
            False,
            "O identificador AnyDesk contém muitos caracteres especiais. "
            "Não importar credenciais sensíveis em texto puro."
        )

    # Permitir apenas alfanuméricos e hífen
    # Rejeitar símbolos típicos de senha como @, !, $, _, etc.
    caracteres_proibidos = set("!@#$%^&*()[]{}/<>\\|:;\"'_")
    if any(c in caracteres_proibidos for c in anydesk_id):
        return (
            False,
            "O identificador AnyDesk contém caracteres inválidos. "
            "Use apenas letras, números e hífen."
        )

    return True, ""


def normalizar_valor_monetario(valor: str | None) -> str | None:
    """
    Normaliza valor monetário para formato decimal canônico com ponto.

    Exemplos aceitos:
    - "R$ 1.250,00" -> "1250.00"
    - "1250,5"      -> "1250.50"
    - "1250.50"     -> "1250.50"
    """
    bruto = (valor or "").strip()
    if not bruto:
        return None

    sem_moeda = bruto.replace("R$", "").replace(" ", "")

    # Quando há vírgula, assume padrão pt-BR com ponto de milhar.
    if "," in sem_moeda:
        sem_moeda = sem_moeda.replace(".", "").replace(",", ".")

    try:
        numero = float(sem_moeda)
    except ValueError as exc:
        raise ValueError("O campo valor deve ser numérico.") from exc

    if numero < 0:
        raise ValueError("O campo valor não pode ser negativo.")

    return f"{numero:.2f}"


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


def validar_tipo_ativo(tipo_ativo: str) -> tuple[bool, str]:
    """
    Valida o tipo oficial do ativo usado pela nova UI.
    """
    tipo_ativo = (tipo_ativo or "").strip().title()

    if not tipo_ativo:
        return False, "O tipo do ativo não pode ficar vazio."

    if tipo_ativo not in TIPOS_ATIVO_VALIDOS:
        return False, f"Tipo de ativo inválido. Use um destes: {', '.join(TIPOS_ATIVO_VALIDOS)}."

    return True, ""


def validar_setor(setor: str) -> tuple[bool, str]:
    """
    Valida se o setor informado é permitido.
    Normaliza a entrada com title() para comparação case-insensitive.
    """
    setor = (setor or "").strip().title()

    if not setor:
        return False, "O setor não pode ficar vazio."

    if setor not in SETORES_VALIDOS:
        return False, f"Setor inválido. Use um destes: {', '.join(SETORES_VALIDOS)}."

    return True, ""


def validar_condicao(condicao: str | None) -> tuple[bool, str]:
    """
    Valida se a condição informada é permitida.
    Campo opcional — retorna OK se vazio.
    """
    condicao = (condicao or "").strip().title()

    if not condicao:
        return True, ""

    if condicao not in CONDICOES_VALIDAS:
        return False, f"Condição inválida. Use uma delas: {', '.join(CONDICOES_VALIDAS)}."

    return True, ""


# Fase 3 Round 2.1: Validação de unidade/localização padronizada
def validar_unidade(unidade: str | None) -> tuple[bool, str]:
    """
    Valida se a unidade/localização informada está na lista oficial.
    Normaliza com title() para comparação case-insensitive.
    Campo opcional — retorna OK se vazio (compatibilidade com dados legados).
    """
    unidade = (unidade or "").strip().title()

    # Permite vazio para compatibilidade com dados legados que possam não ter unidade
    if not unidade:
        return True, ""

    if unidade not in UNIDADES_VALIDAS:
        return False, f"Unidade inválida. Use uma delas: {', '.join(UNIDADES_VALIDAS)}."

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


def validar_data_nao_futura(data_str: str, nome_campo: str) -> tuple[bool, str]:
    """
    Garante que a data informada não seja posterior ao dia atual.
    """
    ok, msg = validar_data_iso(data_str)
    if not ok:
        return False, msg

    data_valor = datetime.strptime((data_str or "").strip(), "%Y-%m-%d").date()
    if data_valor > date.today():
        return False, f"O campo {nome_campo} não pode ser uma data futura."

    return True, ""


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
    data_saida: str | None,
    data_compra: str | None = None,
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

    ok, msg = validar_data_nao_futura(data_entrada, "data_entrada")
    if not ok:
        return False, msg

    ok, msg = validar_data_iso_opcional(data_saida_fmt)
    if not ok:
        return False, msg

    ok, msg = validar_data_iso_opcional(data_compra)
    if not ok:
        return False, msg

    ok, msg = comparar_datas(data_entrada, data_saida_fmt)
    if not ok:
        return False, msg

    if data_compra:
        ok, msg = comparar_datas(data_compra, data_entrada)
        if not ok:
            return False, "A data da compra não pode ser maior que a data de entrada."

    if status_fmt == "Baixado" and not data_saida_fmt:
        return False, "Ativos com status 'Baixado' devem possuir data de saída."

    if status_fmt == "Disponível" and data_saida_fmt:
        return False, "Ativos com status 'Disponível' não devem possuir data de saída."

    if status_fmt == "Em Uso" and not usuario_fmt:
        return False, "Ativos com status 'Em Uso' devem possuir responsável."

    return True, ""


def validar_especificacoes_por_tipo(ativo, tipo_principal: str) -> tuple[bool, str]:
    """
    Valida coerência mínima das especificações técnicas por tipo.

    Nesta etapa, monitor foi simplificado para manter apenas `polegadas`.
    Os demais campos legados de monitor continuam opcionais para compatibilidade,
    sem exigência no fluxo atual.
    """
    tipo_fmt = (tipo_principal or "").strip().title()

    if tipo_fmt != "Monitor":
        return True, ""

    ok, msg = validar_texto_opcional(getattr(ativo, "polegadas", None), "polegadas", tamanho_maximo=40)
    if not ok:
        return False, msg

    # Campos legados aceitos apenas como compatibilidade histórica.
    for nome_campo in ["resolucao", "tipo_painel", "entrada_video", "fonte_ou_cabo"]:
        ok, msg = validar_texto_opcional(getattr(ativo, nome_campo, None), nome_campo, tamanho_maximo=120)
        if not ok:
            return False, msg

    return True, ""


def validar_ativo(ativo, *, validar_id: bool = True) -> None:
    """
    Valida o objeto Ativo completo.
    validar_id=False é usado na criação quando o ID ainda não foi gerado pelo backend.
    """
    if validar_id:
        ok, msg = validar_id_ativo(ativo.id_ativo)
        if not ok:
            raise ValueError(msg)

    # `tipo_ativo` é o campo oficial; `tipo` segue apenas como compatibilidade legada.
    tipo_principal = getattr(ativo, "tipo_ativo", None) or ativo.tipo
    # `setor` é o campo oficial; `departamento` segue apenas como compatibilidade legada.
    setor_principal = getattr(ativo, "setor", None) or ativo.departamento

    for valor, nome in [
        (tipo_principal, "tipo_ativo"),
        (ativo.marca, "marca"),
        (ativo.modelo, "modelo"),
        (setor_principal, "setor"),
    ]:
        ok, msg = validar_texto_obrigatorio(valor, nome)
        if not ok:
            raise ValueError(msg)

    ok, msg = validar_tipo_ativo(tipo_principal)
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_especificacoes_por_tipo(ativo, tipo_principal)
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_setor(setor_principal)
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_texto_obrigatorio(getattr(ativo, "descricao", ""), "descricao", tamanho_maximo=255)
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_texto_obrigatorio(getattr(ativo, "categoria", ""), "categoria")
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_texto_opcional(getattr(ativo, "codigo_interno", None), "codigo_interno", tamanho_maximo=50)
    if not ok:
        raise ValueError(msg)

    codigo_interno = (getattr(ativo, "codigo_interno", None) or "").strip().upper()
    if codigo_interno and not CODIGO_INTERNO_REGEX.match(codigo_interno):
        raise ValueError("O campo codigo_interno contém caracteres inválidos.")

    ok, msg = validar_texto_opcional(getattr(ativo, "serial", None), "serial", tamanho_maximo=120)
    if not ok:
        raise ValueError(msg)

    serial = (getattr(ativo, "serial", None) or "").strip().upper()
    if serial and not SERIAL_REGEX.match(serial):
        raise ValueError("O campo serial contém caracteres inválidos.")

    ok, msg = validar_condicao(getattr(ativo, "condicao", None))
    if not ok:
        raise ValueError(msg)

    # Fase 3 Round 2.1: Validar unidade/localização
    ok, msg = validar_unidade(getattr(ativo, "localizacao", None))
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_texto_opcional(getattr(ativo, "localizacao", None), "localizacao", tamanho_maximo=120)
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_texto_opcional(getattr(ativo, "email_responsavel", None), "email_responsavel", tamanho_maximo=255)
    if not ok:
        raise ValueError(msg)

    email_responsavel = (getattr(ativo, "email_responsavel", "") or "").strip()
    if email_responsavel and not validar_email(email_responsavel):
        raise ValueError("O campo email_responsavel possui formato inválido.")

    ok, msg = validar_texto_opcional(ativo.usuario_responsavel, "usuario_responsavel")
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_numero_linha(getattr(ativo, "numero_linha", None))
    if not ok:
        raise ValueError(msg)

    # IMEI removido em Fase 3 Round 3 — não mais validado no fluxo de celular

    ok, msg = validar_texto_opcional(getattr(ativo, "detalhes_tecnicos", None), "detalhes_tecnicos", tamanho_maximo=255)
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_texto_opcional(getattr(ativo, "observacoes", None), "observacoes", tamanho_maximo=5000)
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_data_iso_opcional(getattr(ativo, "data_compra", None))
    if not ok:
        raise ValueError(msg)

    valor_bruto = (getattr(ativo, "valor", None) or "").strip()
    if valor_bruto:
        # Reaproveita normalização central para manter consistência entre frontend e backend.
        normalizar_valor_monetario(valor_bruto)

    ok, msg = validar_texto_opcional(ativo.nota_fiscal, "nota_fiscal")
    if not ok:
        raise ValueError(msg)

    # Valida o campo opcional de garantia mantendo o mesmo limite textual.
    ok, msg = validar_texto_opcional(ativo.garantia, "garantia")
    if not ok:
        raise ValueError(msg)

    # Validar identificadores de acesso remoto (TeamViewer e AnyDesk)
    ok, msg = validar_teamviewer_id(getattr(ativo, "teamviewer_id", None))
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_anydesk_id(getattr(ativo, "anydesk_id", None))
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_status(ativo.status)
    if not ok:
        raise ValueError(msg)

    ok, msg = validar_regras_ativo(
        ativo.status,
        ativo.usuario_responsavel,
        ativo.data_entrada,
        ativo.data_saida,
        getattr(ativo, "data_compra", None),
    )
    if not ok:
        raise ValueError(msg)     
              
