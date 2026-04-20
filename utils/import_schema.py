# utils/import_schema.py
#
# Esquema de domínio para reconhecimento flexível de colunas em importação de ativos.
# Centraliza dicionários de sinônimos, campos críticos e regras de validação.
#
# Objetivo: permitir que o motor de matching reconheça variações de cabeçalho
# sem exigir normalização manual da planilha.
#

from enum import Enum
from typing import Dict, List, Set

# ============================================================================
# DEFINIÇÃO DE CAMPOS E CRITICIDADE
# ============================================================================

class CriticalidadeCampo(Enum):
    """
    Nível de criticidade de um campo para importação.
    - CRITICO: Campo obrigatório; sem mapeamento válido, importação bloqueada.
    - OBRIGATORIO_COM_INFERENCIA: Campo obrigatório, mas pode ser inferido.
    - OPCIONAL: Campo sem impacto na importação se ausente.
    """
    CRITICO = "critico"
    OBRIGATORIO_COM_INFERENCIA = "obrigatorio_com_inferencia"
    OPCIONAL = "opcional"


# Mapa de campos do domínio e sua criticidade
CRITICIDADE_CAMPOS = {
    # Campos críticos — bloqueiam se não mapeados
    "tipo_ativo": CriticalidadeCampo.CRITICO,
    "marca": CriticalidadeCampo.CRITICO,
    "modelo": CriticalidadeCampo.CRITICO,
    "setor": CriticalidadeCampo.CRITICO,
    "data_entrada": CriticalidadeCampo.CRITICO,

    # Campos obrigatórios mas com fallback/inferência
    "status": CriticalidadeCampo.OBRIGATORIO_COM_INFERENCIA,  # fallback: "Disponível"
    "categoria": CriticalidadeCampo.OBRIGATORIO_COM_INFERENCIA,  # inferência: tipo_ativo
    "descricao": CriticalidadeCampo.OBRIGATORIO_COM_INFERENCIA,  # inferência: tipo+marca+modelo

    # Campos opcionais — não bloqueiam se ausentes
    "codigo_interno": CriticalidadeCampo.OPCIONAL,
    "serial": CriticalidadeCampo.OPCIONAL,
    "usuario_responsavel": CriticalidadeCampo.OPCIONAL,
    "email_responsavel": CriticalidadeCampo.OPCIONAL,
    "localizacao": CriticalidadeCampo.OPCIONAL,
    "condicao": CriticalidadeCampo.OPCIONAL,
    "data_saida": CriticalidadeCampo.OPCIONAL,
    "data_compra": CriticalidadeCampo.OPCIONAL,
    "valor": CriticalidadeCampo.OPCIONAL,
    "observacoes": CriticalidadeCampo.OPCIONAL,
    "detalhes_tecnicos": CriticalidadeCampo.OPCIONAL,
    "processador": CriticalidadeCampo.OPCIONAL,
    "ram": CriticalidadeCampo.OPCIONAL,
    "armazenamento": CriticalidadeCampo.OPCIONAL,
    "sistema_operacional": CriticalidadeCampo.OPCIONAL,
    "carregador": CriticalidadeCampo.OPCIONAL,
    "teamviewer_id": CriticalidadeCampo.OPCIONAL,
    "anydesk_id": CriticalidadeCampo.OPCIONAL,
    "nome_equipamento": CriticalidadeCampo.OPCIONAL,
    "hostname": CriticalidadeCampo.OPCIONAL,
    "numero_linha": CriticalidadeCampo.OPCIONAL,
    "operadora": CriticalidadeCampo.OPCIONAL,
    "conta_vinculada": CriticalidadeCampo.OPCIONAL,
    "polegadas": CriticalidadeCampo.OPCIONAL,
    "resolucao": CriticalidadeCampo.OPCIONAL,
    "tipo_painel": CriticalidadeCampo.OPCIONAL,
    "entrada_video": CriticalidadeCampo.OPCIONAL,
    "fonte_ou_cabo": CriticalidadeCampo.OPCIONAL,
    "nota_fiscal": CriticalidadeCampo.OPCIONAL,
    "garantia": CriticalidadeCampo.OPCIONAL,
}

# ============================================================================
# SINÔNIMOS DE CAMPOS DO DOMÍNIO
# ============================================================================

# Mapa de sinônimos: variação → campo oficial
# Usado pelo motor de matching para reconhecer nomes alternativos
# Todos os aliases aqui são tolerados e mapeados automaticamente com score 0.95
#
# NOTA: Esta matriz é gerada internamente para matching.
# Os valores estão normalizados (minúsculas, sem acentos, espaços colapsados)
SINONIMOS_CAMPOS = {
    # ========== tipo_ativo — equipamento / classe / categoria ==========
    "tipo": "tipo_ativo",
    "tipo ativo": "tipo_ativo",
    "tipo do ativo": "tipo_ativo",
    "tipo de ativo": "tipo_ativo",
    "categoria ativo": "tipo_ativo",
    "classe": "tipo_ativo",
    "categoria equipamento": "tipo_ativo",
    "tipo equipamento": "tipo_ativo",
    "ativo": "tipo_ativo",
    "descricao item": "tipo_ativo",
    "classe equipamento": "tipo_ativo",
    "natureza item": "tipo_ativo",
    "especificacao item": "tipo_ativo",
    "item": "tipo_ativo",
    "equipamento": "tipo_ativo",

    # ========== marca — fabricante / vendor / produtor ==========
    "marca": "marca",
    "fabricante": "marca",
    "vendor": "marca",
    "fabricante marca": "marca",
    "marca fabricante": "marca",
    "brand": "marca",
    "produtor": "marca",
    "maker": "marca",
    "manufacture": "marca",
    "manufacturer": "marca",

    # ========== modelo — version / referencia / linha ==========
    "modelo": "modelo",
    "model": "modelo",
    "modelo equipamento": "modelo",
    "versao modelo": "modelo",
    "referencia modelo": "modelo",
    "versao": "modelo",
    "reference": "modelo",
    "linha": "modelo",
    "denominacao modelo": "modelo",

    # ========== codigo_interno — patrimonio / tombo / numero patrimonial ==========
    "patrimonio": "codigo_interno",
    "patrimonio interno": "codigo_interno",
    "tombo": "codigo_interno",
    "numero patrimonial": "codigo_interno",
    "nro patrimonio": "codigo_interno",
    "numero patrimonio": "codigo_interno",
    "cod interno": "codigo_interno",
    "codigo interno": "codigo_interno",
    "codigo patrimonial": "codigo_interno",
    "id patrimonial": "codigo_interno",
    "plaqueta": "codigo_interno",
    "etiqueta patrimonial": "codigo_interno",
    "numero tombo": "codigo_interno",
    "numero ativo": "codigo_interno",
    "id ativo": "codigo_interno",
    "numero inventario": "codigo_interno",

    # ========== usuario_responsavel — responsavel / colaborador / custodiante ==========
    "responsavel": "usuario_responsavel",
    "usuario responsavel": "usuario_responsavel",
    "responsavel usuario": "usuario_responsavel",
    "colaborador": "usuario_responsavel",
    "portador": "usuario_responsavel",
    "custodiante": "usuario_responsavel",
    "atribuida para": "usuario_responsavel",
    "alocado para": "usuario_responsavel",
    "alocado a": "usuario_responsavel",
    "funcionario": "usuario_responsavel",
    "usuario": "usuario_responsavel",
    "nome responsavel": "usuario_responsavel",
    "quem usa": "usuario_responsavel",
    "proprietario": "usuario_responsavel",
    "proprietario equipamento": "usuario_responsavel",
    "designado": "usuario_responsavel",
    "pessoa responsavel": "usuario_responsavel",

    # ========== email_responsavel — email / contato ==========
    "email responsavel": "email_responsavel",
    "e mail responsavel": "email_responsavel",
    "mail responsavel": "email_responsavel",
    "contato responsavel": "email_responsavel",
    "email usuario": "email_responsavel",
    "email colaborador": "email_responsavel",
    "email": "email_responsavel",
    "e-mail": "email_responsavel",
    "endereco email": "email_responsavel",
    "email collab": "email_responsavel",

    # ========== setor — departamento / area / lotacao ==========
    "departamento": "setor",
    "area": "setor",
    "unidade": "setor",
    "unidade organizacional": "setor",
    "setor departamento": "setor",
    "departamento unidade": "setor",
    "lotacao": "setor",
    "gerencia": "setor",
    "gerência": "setor",
    "centro custo": "setor",
    "centro de custo": "setor",
    "equipe": "setor",
    "secao": "setor",
    "secção": "setor",
    "divisao": "setor",
    "divisão": "setor",
    "ramo": "setor",

    # ========== localizacao — local / sala / andar / predio ==========
    "local": "localizacao",
    "filial": "localizacao",
    "site": "localizacao",
    "base": "localizacao",
    "sala": "localizacao",
    "andar": "localizacao",
    "unidade localizacao": "localizacao",
    "unidade fisica": "localizacao",
    "unidade física": "localizacao",
    "local estoque": "localizacao",
    "predio": "localizacao",
    "prédio": "localizacao",
    "bloco": "localizacao",
    "pavimento": "localizacao",
    "endereco interno": "localizacao",
    "endereço interno": "localizacao",
    "posicao": "localizacao",
    "posição": "localizacao",
    "lugar": "localizacao",

    # ========== status — situacao / estado / disponibilidade ==========
    "status": "status",
    "situacao": "status",
    "situação": "status",
    "estado": "status",
    "condicao operacional": "status",
    "condição operacional": "status",
    "disponibilidade": "status",
    "situacao ativo": "status",
    "estado equipamento": "status",
    "status equipamento": "status",

    # ========== data_entrada — entrada / recebimento / cadastro ==========
    "entrada": "data_entrada",
    "data entrada": "data_entrada",
    "data de entrada": "data_entrada",
    "dt entrada": "data_entrada",
    "data recebimento": "data_entrada",
    "data de recebimento": "data_entrada",
    "data cadastro": "data_entrada",
    "data criacao": "data_entrada",
    "data criação": "data_entrada",
    "recebimento": "data_entrada",
    "data incorporacao": "data_entrada",
    "data incorporação": "data_entrada",
    "data ingresso": "data_entrada",
    "data aquisicao": "data_entrada",
    "data aquisição": "data_entrada",
    "data chegada": "data_entrada",

    # ========== data_saida — saida / baixa / devolucao ==========
    "data saida": "data_saida",
    "data saída": "data_saida",
    "dt saida": "data_saida",
    "saida": "data_saida",
    "saída": "data_saida",
    "data baixa": "data_saida",
    "data devolucao": "data_saida",
    "data devolução": "data_saida",
    "data desativacao": "data_saida",
    "data desativação": "data_saida",
    "data remocao": "data_saida",
    "data remoção": "data_saida",
    "quando saiu": "data_saida",

    # ========== data_compra — compra / aquisicao / emissao nf ==========
    "compra": "data_compra",
    "data compra": "data_compra",
    "dt compra": "data_compra",
    "aquisicao": "data_compra",
    "aquisição": "data_compra",
    "data aquisicao": "data_compra",
    "data nf": "data_compra",
    "emissao compra": "data_compra",
    "emissão compra": "data_compra",
    "data emissao nf": "data_compra",
    "quando foi comprado": "data_compra",
    "data procura": "data_compra",

    # ========== condicao — estado / operacional ==========
    "condicao": "condicao",
    "condição": "condicao",
    "condicao equipamento": "condicao",
    "condição equipamento": "condicao",
    "estado": "condicao",
    "estado equipamento": "condicao",
    "condicao uso": "condicao",
    "condição uso": "condicao",

    # ========== serial — numero serie / sn / service tag ==========
    "serial": "serial",
    "numero serie": "serial",
    "número série": "serial",
    "nro serie": "serial",
    "num serie": "serial",
    "sn": "serial",
    "service tag": "serial",
    "identificador fabricante": "serial",
    "numero serial": "serial",
    "número serial": "serial",
    "ns": "serial",
    "numero identificacao": "serial",
    "numero identificacao fabricante": "serial",

    # ========== nota_fiscal — nf / invoice / documento fiscal ==========
    "nota fiscal": "nota_fiscal",
    "nota-fiscal": "nota_fiscal",
    "nf": "nota_fiscal",
    "numero nf": "nota_fiscal",
    "número nf": "nota_fiscal",
    "nro nf": "nota_fiscal",
    "chave nf": "nota_fiscal",
    "documento fiscal": "nota_fiscal",
    "invoice number": "nota_fiscal",
    "numero nota fiscal": "nota_fiscal",
    "numero nota": "nota_fiscal",
    "numero documento": "nota_fiscal",
    "doc": "nota_fiscal",
    "numero fiscal": "nota_fiscal",
    "serie nf": "nota_fiscal",
    "serie nota fiscal": "nota_fiscal",

    # ========== garantia — prazo / validade / cobertura ==========
    "garantia": "garantia",
    "prazo garantia": "garantia",
    "validade garantia": "garantia",
    "fim garantia": "garantia",
    "garantia ate": "garantia",
    "garantia até": "garantia",
    "cobertura": "garantia",
    "periodo garantia": "garantia",
    "período garantia": "garantia",
    "tempo garantia": "garantia",
    "meses garantia": "garantia",
    "anos garantia": "garantia",
    "data garantia": "garantia",
    "data fim garantia": "garantia",
    "plano garantia": "garantia",
    "tipo garantia": "garantia",

    # ========== observacoes — obs / notas / comentario ==========
    "observacoes": "observacoes",
    "observações": "observacoes",
    "observacao": "observacoes",
    "observação": "observacoes",
    "obs": "observacoes",
    "notas": "observacoes",
    "nota": "observacoes",
    "comentario": "observacoes",
    "comentários": "observacoes",
    "descricao livre": "observacoes",
    "descricao adicional": "observacoes",
    "detalhes": "observacoes",
    "detalhes adicionais": "observacoes",
    "informacoes adicionais": "observacoes",
    "observacoes adicionais": "observacoes",
    "campo livre": "observacoes",
    "anotacoes": "observacoes",
    "anotações": "observacoes",
    "remarques": "observacoes",
    "historico": "observacoes",
    "histórico": "observacoes",

    # ========== fornecedor — vendor / produtor / empresa ==========
    "fornecedor": "fornecedor",
    "vendor": "fornecedor",
    "vendedor": "vendedor",
    "fornecedor principal": "fornecedor",
    "fornecedor equipamento": "fornecedor",
    "empresa fornecedora": "fornecedor",
    "nome fornecedor": "fornecedor",
    "company": "fornecedor",
    "empresa": "fornecedor",
}

# ============================================================================
# VALORES VÁLIDOS POR CAMPO ENUMERADO
# ============================================================================

# Sinônimos de valores para campos com domínio limitado
SINONIMOS_VALORES = {
    # Mapeamento de tipos de ativo: variação → tipo oficial
    "tipos_ativo": {
        "notebook": "Notebook",
        "computador portatil": "Notebook",
        "laptop": "Notebook",
        "note": "Notebook",
        "ultrabook": "Notebook",

        "desktop": "Desktop",
        "computador": "Desktop",
        "pc": "Desktop",
        "computador desktop": "Desktop",
        "estacao": "Desktop",
        "workstation": "Desktop",

        "celular": "Celular",
        "smartphone": "Celular",
        "telefone": "Celular",
        "mobile": "Celular",

        "monitor": "Monitor",
        "tela": "Monitor",
        "display": "Monitor",

        "mouse": "Mouse",
        "rato": "Mouse",

        "teclado": "Teclado",

        "headset": "Headset",
        "fone": "Headset",
        "headphone": "Headset",
        "audio": "Headset",

        "adaptador": "Adaptador",
        "conversor": "Adaptador",

        "cabo": "Cabo",
        "cordao": "Cabo",

        "carregador": "Carregador",
        "fonte": "Carregador",
        "bateria": "Carregador",

        "outro": "Outro",
        "diversos": "Outro",
    },

    # Mapeamento de setores
    "setores": {
        "ti": "T.I",
        "t.i": "T.I",
        "informatica": "T.I",
        "tecnologia informacao": "T.I",

        "rh": "RH",
        "recursos humanos": "RH",
        "gestao pessoas": "RH",

        "adm": "ADM",
        "administracao": "ADM",
        "administrativo": "ADM",

        "financeiro": "Financeiro",
        "financeira": "Financeiro",
        "contabilidade": "Financeiro",

        "vendas": "Vendas",
        "comercial": "Vendas",

        "marketing": "Marketing",
        "comunicacao": "Marketing",

        "infraestrutura": "Infraestrutura",
        "infra": "Infraestrutura",

        "apoio": "Apoio",
        "suporte": "Apoio",

        "estagiarios": "Estagiários",
        "estagio": "Estagiários",

        "diretoria": "Diretoria",
        "direcao": "Diretoria",

        "manutencao": "Manutenção",
        "manutencao": "Manutenção",

        "tecnica": "Técnica",
        "operacoes": "Técnica",

        "logistica": "Logística",

        "licitacao": "Licitação",
    },

    # Mapeamento de status
    "status": {
        "disponivel": "Disponível",
        "disponível": "Disponível",
        "em stock": "Disponível",
        "em estoque": "Disponível",
        "livre": "Disponível",

        "em uso": "Em Uso",
        "usado": "Em Uso",
        "em poder": "Em Uso",
        "alocado": "Em Uso",

        "em manutencao": "Em Manutenção",
        "em manutenção": "Em Manutenção",
        "manutencao": "Em Manutenção",
        "manutenção": "Em Manutenção",
        "em reparo": "Em Manutenção",

        "reservado": "Reservado",
        "reserva": "Reservado",

        "baixado": "Baixado",
        "descontinuado": "Baixado",
        "aposentado": "Baixado",
        "sucateado": "Baixado",
        "fora de uso": "Baixado",
    },

    # Mapeamento de condições
    "condicoes": {
        "novo": "Novo",
        "novo estado": "Novo",

        "bom": "Bom",
        "em bom estado": "Bom",
        "funcionando": "Bom",

        "regular": "Regular",
        "funciona com restricoes": "Regular",

        "ruim": "Ruim",
        "danificado": "Ruim",
        "com defeito": "Ruim",
        "quebrado": "Ruim",

        "inativo": "Inativo",
        "inoperante": "Inativo",
        "nao funciona": "Inativo",
    },
}

# ============================================================================
# CONSTANTES DE MATCHING E PONTUAÇÃO
# ============================================================================

# Limiares de confiança (em %)
LIMIAR_CONFIANCA_ALTA = 90  # Score >= 90: auto-aplica, sem confirmação
LIMIAR_CONFIANCA_MEDIA = 75  # Score >= 75: sugere com pré-seleção
LIMIAR_CONFIANCA_BAIXA = 60  # Score >= 60: sugere sem pré-seleção
LIMIAR_CONFIANCA_REJEITAR = 60  # Score < 60: ignora, não sugere

# Pesos para cálculo de score
PESO_CORRESPONDENCIA_EXATA = 100  # Correspondência exata normalizada
PESO_SINONIMO_OFICIAL = 95  # Sinônimo em dicionário global
PESO_SIMILARIDADE_ALTA = 85  # Distância textual > 0.8
PESO_SIMILARIDADE_MEDIA = 75  # Distância textual 0.7–0.8
PESO_SIMILARIDADE_BAIXA = 60  # Distância textual 0.6–0.7

# Penalidades
PENALIDADE_COLISAO = 20  # Reduz score se outra coluna mapeia melhor
PENALIDADE_INCONSISTENCIA = 15  # Reduz score se coluna tem dados inconsistentes

# ============================================================================
# FUNÇÕES UTILITÁRIAS DE SCHEMA
# ============================================================================

def obter_campos_criticos() -> Set[str]:
    """
    Retorna conjunto de nomes de campos críticos (que bloqueiam importação se não mapeados).
    """
    # Comentário: filtra campos com criticidade CRITICO
    return {
        campo
        for campo, criticidade in CRITICIDADE_CAMPOS.items()
        if criticidade == CriticalidadeCampo.CRITICO
    }


def obter_campos_com_inferencia() -> Set[str]:
    """
    Retorna conjunto de campos que podem ser inferidos quando ausentes.
    """
    # Comentário: status → "Disponível", categoria → tipo_ativo, descricao → composição
    return {
        campo
        for campo, criticidade in CRITICIDADE_CAMPOS.items()
        if criticidade == CriticalidadeCampo.OBRIGATORIO_COM_INFERENCIA
    }


def obter_campos_opcionais() -> Set[str]:
    """
    Retorna conjunto de campos opcionais (não bloqueiam se ausentes).
    """
    # Comentário: campos sem impacto se não forem mapeados
    return {
        campo
        for campo, criticidade in CRITICIDADE_CAMPOS.items()
        if criticidade == CriticalidadeCampo.OPCIONAL
    }


def obter_todos_campos() -> Set[str]:
    """
    Retorna conjunto de todos os campos válidos do schema.
    """
    # Comentário: usado para validação de campo_destino em mapeamento
    return set(CRITICIDADE_CAMPOS.keys())


def obter_sinonimo_campo(coluna_normalizada: str) -> str | None:
    """
    Procura sinônimo de campo no dicionário.
    Retorna campo oficial ou None se não encontrado.
    """
    # Comentário: busca case-insensitive, lowercase já esperado na entrada
    return SINONIMOS_CAMPOS.get(coluna_normalizada.lower())


def obter_sinonimo_valor(tipo_campo: str, valor_normalizado: str) -> str | None:
    """
    Procura sinônimo de valor dentro de um campo enumerado.

    Args:
        tipo_campo: nome do campo (ex: "tipos_ativo", "setores")
        valor_normalizado: valor já normalizado (lowercase)

    Returns:
        Valor oficial ou None.
    """
    # Comentário: útil para normalizar "laptop" → "Notebook"
    mapa_valores = SINONIMOS_VALORES.get(tipo_campo, {})
    return mapa_valores.get(valor_normalizado.lower())


def eh_campo_enumerado(campo: str) -> bool:
    """
    Indica se um campo tem domínio limitado (não é free-text).
    """
    # Comentário: campos enumerados têm sinônimos_valores definidos
    campos_enumerados = {"tipos_ativo", "setores", "status", "condicoes"}
    return campo in campos_enumerados


def obter_campos_por_criticidade(criticidade: CriticalidadeCampo) -> Set[str]:
    """
    Retorna campos com nível de criticidade especificado.
    """
    return {
        campo
        for campo, crit in CRITICIDADE_CAMPOS.items()
        if crit == criticidade
    }


def obter_criticidade_campo(campo: str) -> CriticalidadeCampo | None:
    """
    Retorna nível de criticidade de um campo específico.

    Args:
        campo: Nome do campo

    Returns:
        CriticalidadeCampo ou None se campo não existe
    """
    return CRITICIDADE_CAMPOS.get(campo)
