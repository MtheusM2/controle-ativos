# utils/normalizador_valores_importacao.py
#
# Centraliza normalização de VALORES de domínio para importação.
# Exemplos: mkt → Marketing, rh → RH, ti → T.I, técnica → Técnica
#
# Autor: Claude Code (2026-04-27)
# Objetivo: Resolver problema de valores não-reconhecidos na importação
#

from typing import Optional
import unicodedata

# ===== MAPEAMENTOS DE NORMALIZAÇÃO (2026-04-27) =====
# Estrutura: {padrão_entrada_normalizado: valor_oficial}
# Padrões estão em lowercase, sem espaços, sem pontos

MAPEAMENTO_SETORES = {
    # Marketing
    "marketing": "Marketing",
    "mkt": "Marketing",
    "mktp": "Marketing",
    "marketingp": "Marketing",

    # RH (Recursos Humanos) — CORRIGIDO: "RH" → "Rh" para alinhar com SETORES_VALIDOS em validators.py
    "recursoshumanos": "Rh",
    "rh": "Rh",
    "rhh": "Rh",
    "hh": "Rh",
    "recursos": "Rh",

    # T.I (Tecnologia da Informação)
    "tecnologiadainformacao": "T.I",
    "ti": "T.I",
    "tinfo": "T.I",
    "sistemas": "T.I",
    "si": "T.I",
    "informatica": "T.I",

    # Administração
    "administracao": "Adm",
    "admin": "Adm",
    "adm": "Adm",
    "administrativo": "Adm",
    "admtva": "Adm",

    # Técnica
    "tecnica": "Técnica",
    "tecnico": "Técnica",
    "tec": "Técnica",
    "tecnicaoperacional": "Técnica",

    # Financeiro
    "financeiro": "Financeiro",
    "fin": "Financeiro",
    "financeira": "Financeiro",
    "cf": "Financeiro",
    "controloria": "Financeiro",

    # Operações
    "operacoes": "Operações",
    "op": "Operações",
    "ops": "Operações",
    "operacional": "Operações",

    # Vendas
    "vendas": "Vendas",
    "vnd": "Vendas",
    "sales": "Vendas",
    "v": "Vendas",
    "comercial": "Vendas",

    # Diretoria
    "diretoria": "Diretoria",
    "diretor": "Diretoria",
    "dir": "Diretoria",
    "diretivo": "Diretoria",
    "executivo": "Diretoria",
}

# ===== MAPEAMENTO DE STATUS (2026-04-28) =====
# Normaliza variações de status para valores canônicos
# NOTA: Chaves devem estar SEM espaços (função remove espaços para busca)
MAPEAMENTO_STATUS = {
    # Disponível
    "disponivel": "Disponível",
    "livre": "Disponível",
    "emstock": "Disponível",

    # Em Uso
    "emuso": "Em Uso",
    "usado": "Em Uso",
    "alocado": "Em Uso",

    # Em Manutenção
    "emmanutencao": "Em Manutenção",
    "manutencao": "Em Manutenção",
    "reparo": "Em Manutenção",

    # Reservado
    "reservado": "Reservado",
    "reserva": "Reservado",

    # Baixado
    "baixado": "Baixado",
    "descontinuado": "Baixado",
    "aposentado": "Baixado",
    "sucateado": "Baixado",
}

# ===== MAPEAMENTO DE TIPOS DE ATIVO (2026-04-28) =====
# Normaliza variações de tipo de ativo para valores canônicos
# NOTA: Chaves devem estar SEM espaços (função remove espaços para busca)
MAPEAMENTO_TIPOS_ATIVO = {
    # Notebook
    "notebook": "Notebook",
    "computadorportatil": "Notebook",  # computador portátil (sem espaço, sem acento)
    "laptop": "Notebook",
    "note": "Notebook",
    "ultrabook": "Notebook",

    # Desktop
    "desktop": "Desktop",
    "computador": "Desktop",
    "pc": "Desktop",
    "computadordesktop": "Desktop",
    "estacao": "Desktop",
    "workstation": "Desktop",

    # Celular
    "celular": "Celular",
    "smartphone": "Celular",
    "telefone": "Celular",
    "mobile": "Celular",
    "phone": "Celular",

    # Monitor
    "monitor": "Monitor",
    "tela": "Monitor",
    "display": "Monitor",

    # Mouse
    "mouse": "Mouse",
    "rato": "Mouse",

    # Teclado
    "teclado": "Teclado",
    "keyboard": "Teclado",

    # Headset
    "headset": "Headset",
    "fone": "Headset",
    "headphone": "Headset",
    "audio": "Headset",

    # Adaptador
    "adaptador": "Adaptador",
    "conversor": "Adaptador",

    # Cabo
    "cabo": "Cabo",
    "cordao": "Cabo",

    # Carregador
    "carregador": "Carregador",
    "fonte": "Carregador",
    "bateria": "Carregador",

    # Outro
    "outro": "Outro",
    "diversos": "Outro",
}


def _normalizar_valor_generico(valor: Optional[str], mapa_valores: dict) -> Optional[str]:
    """
    Utilitário privado para normalizar valor contra um mapa de sinônimos.

    Args:
        valor: String bruta (pode conter espaços, acentos, maiúsculas)
        mapa_valores: Dicionário {entrada_normalizada: valor_oficial}

    Returns:
        Valor normalizado ou original se não encontrado no mapa.
    """
    if not valor:
        return None

    # Limpar para busca
    valor_limpo = (valor or "").strip()
    if not valor_limpo:
        return None

    # Remover acentos para matching robusto
    valor_sem_acento = ''.join(
        c for c in unicodedata.normalize('NFD', valor_limpo)
        if unicodedata.category(c) != 'Mn'
    )

    # Versão de busca: lowercase, sem espaços, sem pontos, sem underscores
    valor_busca = valor_sem_acento.lower().replace(" ", "").replace(".", "").replace("_", "")

    # Buscar no mapa
    if valor_busca in mapa_valores:
        return mapa_valores[valor_busca]

    # Se não encontrar, retornar original (validador fará validação enum depois)
    return valor_limpo


def normalizar_valor_setor(valor: Optional[str]) -> Optional[str]:
    """
    Normaliza valor de setor/departamento.

    Exemplos:
        "mkt" → "Marketing"
        "RH" → "Rh"
        "t.i." → "T.I"
        "Técnico" → "Técnica"
        "" → None
        None → None

    Args:
        valor: String bruta do setor (pode conter espaços, pontos, maiúsculas)

    Returns:
        Valor normalizado (canônico do sistema) ou None se vazio.
    """
    return _normalizar_valor_generico(valor, MAPEAMENTO_SETORES)


def normalizar_valor_status(valor: Optional[str]) -> Optional[str]:
    """
    Normaliza valor de status/situação do ativo.

    Exemplos:
        "disponível" → "Disponível"
        "em uso" → "Em Uso"
        "em manutenção" → "Em Manutenção"
        "" → None
        None → None

    Args:
        valor: String bruta do status

    Returns:
        Valor normalizado (canônico do sistema) ou None se vazio.
    """
    return _normalizar_valor_generico(valor, MAPEAMENTO_STATUS)


def normalizar_valor_tipo_ativo(valor: Optional[str]) -> Optional[str]:
    """
    Normaliza valor de tipo de ativo (equipamento).

    Exemplos:
        "notebook" → "Notebook"
        "computador portatil" → "Notebook"
        "desktop" → "Desktop"
        "celular" → "Celular"
        "" → None
        None → None

    Args:
        valor: String bruta do tipo de ativo

    Returns:
        Valor normalizado (canônico do sistema) ou None se vazio.
    """
    return _normalizar_valor_generico(valor, MAPEAMENTO_TIPOS_ATIVO)


def normalizar_dados_importacao_valores(dados: dict) -> dict:
    """
    Aplica normalização de VALORES em um dicionário de dados mapeados.

    Nota: Esta função normaliza VALORES de campos, não NOMES de campos.
    Nomes de campos já foram normalizados durante mapeamento.

    Args:
        dados: Dict de {campo: valor} em formato canônico (após mapeamento)

    Returns:
        Dict com valores normalizados conforme mapeamentos centralizados

    Campos Normalizados (2026-04-28):
        - tipo_ativo: aplica MAPEAMENTO_TIPOS_ATIVO
        - setor: aplica MAPEAMENTO_SETORES
        - status: aplica MAPEAMENTO_STATUS
    """
    resultado = dict(dados)

    # ===== NORMALIZAR TIPO_ATIVO (se presente) =====
    if 'tipo_ativo' in resultado and resultado['tipo_ativo']:
        valor_normalizado = normalizar_valor_tipo_ativo(resultado['tipo_ativo'])
        if valor_normalizado:
            resultado['tipo_ativo'] = valor_normalizado

    # ===== NORMALIZAR SETOR (se presente) =====
    if 'setor' in resultado and resultado['setor']:
        valor_normalizado = normalizar_valor_setor(resultado['setor'])
        if valor_normalizado:
            resultado['setor'] = valor_normalizado

    # ===== NORMALIZAR STATUS (se presente) =====
    if 'status' in resultado and resultado['status']:
        valor_normalizado = normalizar_valor_status(resultado['status'])
        if valor_normalizado:
            resultado['status'] = valor_normalizado

    return resultado
