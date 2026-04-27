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
    "tecnologia": "T.I",
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

    # Técnica (removidos acentos automaticamente durante busca)
    "tecnica": "Técnica",
    "tecnico": "Técnica",
    "tec": "Técnica",
    "tecnica_operacional": "Técnica",

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


def normalizar_valor_setor(valor: Optional[str]) -> Optional[str]:
    """
    Normaliza valor de setor/departamento.

    Exemplos:
        "mkt" → "Marketing"
        "RH" → "RH"
        "t.i." → "T.I"
        "Técnico" → "Técnica"
        "" → None
        None → None

    Args:
        valor: String bruta do setor (pode conter espaços, pontos, maiúsculas)

    Returns:
        Valor normalizado (canônico do sistema) ou None se vazio.
        Se não encontrar mapeamento, retorna o valor original normalizado.

    Comportamento:
        - Remove espaços, pontos, underscores
        - Converte para lowercase para busca
        - Preserva maiúsculas no valor de retorno (segue padrão oficial)
        - Retorna valor original se não encontrar no mapeamento (sistema validará depois)
    """
    if not valor:
        return None

    # ===== NORMALIZAR: limpar para busca =====
    valor_limpo = (valor or "").strip()
    if not valor_limpo:
        return None

    # ===== NOVO (2026-04-27): Remover acentos para matching mais robusto =====
    # Exemplo: "Técnico" → "tecnico" (sem acento) → mapeado para "Técnica"
    # Decompomos Unicode em base + combinadores, depois removemos combinadores
    valor_sem_acento = ''.join(
        c for c in unicodedata.normalize('NFD', valor_limpo)
        if unicodedata.category(c) != 'Mn'  # Mn = Mark, Nonspacing (acentos)
    )

    # Criar versão de busca: lowercase, sem espaços, sem pontos, sem underscores
    valor_busca = valor_sem_acento.lower().replace(" ", "").replace(".", "").replace("_", "")

    # ===== BUSCAR NO MAPEAMENTO =====
    if valor_busca in MAPEAMENTO_SETORES:
        valor_oficial = MAPEAMENTO_SETORES[valor_busca]
        # Log para auditoria (útil para entender normalizações aplicadas)
        # Comentário: log será feito no serviço que chamar esta função
        return valor_oficial

    # ===== SE NÃO ENCONTRAR MAPEAMENTO =====
    # Retornar original (sistema aplicará validação de enum depois)
    # Isso permite que erros de validação sejam claros
    return valor_limpo


def normalizar_dados_importacao_valores(dados: dict) -> dict:
    """
    Aplica normalização de VALORES em um dicionário de dados mapeados.

    Nota: Esta função normaliza VALORES de campos, não NOMES de campos.
    Nomes de campos já foram normalizados durante mapeamento.

    Args:
        dados: Dict de {campo: valor} em formato canônico (após mapeamento)

    Returns:
        Dict com valores normalizados conforme mapeamentos centralizados

    Campos Normalizados:
        - setor: aplica MAPEAMENTO_SETORES
    """
    resultado = dict(dados)

    # ===== NORMALIZAR SETOR (se presente) =====
    if 'setor' in resultado and resultado['setor']:
        valor_normalizado = normalizar_valor_setor(resultado['setor'])
        if valor_normalizado:
            resultado['setor'] = valor_normalizado

    # ===== POSSO ADICIONAR MAIS NORMALIZAÇÕES AQUI =====
    # Estrutura aberta para:
    # - normalizar_valor_status()
    # - normalizar_valor_condicao()
    # - normalizar_valor_tipo_ativo()
    # Por agora, apenas setor é crítico (mais usado em CSVs com abreviações)

    return resultado
