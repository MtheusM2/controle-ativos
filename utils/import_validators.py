# utils/import_validators.py
#
# Validadores de segurança operacional para importação em lote.
# Implementa todas as regras definidas em REGRAS_SEGURANCA_IMPORTACAO_DEFINITIVA.md
#
# Responsabilidades:
# - Validar campos críticos e dados
# - Detectar duplicatas
# - Calcular taxa de erro
# - Gerar avisos vs erros
# - Emitir bloqueios
#

import re
from datetime import datetime, date
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from utils.validators import STATUS_VALIDOS as STATUS_VALIDOS_DOMINIO


# Contrato canônico da importação em massa.
# Estes nomes representam o domínio único no backend.
CAMPOS_CANONICOS_IMPORTACAO = {
    'tipo_ativo',
    'marca',
    'modelo',
    'setor',
    'localizacao',
    'status',
    'data_entrada',
    'email_responsavel',
}


# Aliases aceitos somente na entrada por compatibilidade.
# Depois da normalização, o backend trabalha apenas com campos canônicos.
ALIASES_CAMPOS_IMPORTACAO = {
    'departamento': 'setor',
    'unidade': 'localizacao',
    'base': 'localizacao',
    'tipo': 'tipo_ativo',
}


def normalizar_campo_importacao(nome_campo: str | None) -> str:
    """Normaliza o nome de campo para chave canônica de importação."""
    campo = (nome_campo or '').strip().lower()
    if not campo:
        return ''
    return ALIASES_CAMPOS_IMPORTACAO.get(campo, campo)


def normalizar_dados_importacao(linha: Dict[str, str] | None) -> Dict[str, str]:
    """Consolida aliases de entrada em um payload canônico único."""
    linha = linha or {}
    normalizada: Dict[str, str] = {}

    for chave, valor in linha.items():
        campo_canonico = normalizar_campo_importacao(chave)
        if not campo_canonico:
            continue

        # Mantém o primeiro valor não vazio para evitar sobrescrita silenciosa entre aliases.
        valor_limpo = '' if valor is None else str(valor).strip()
        valor_existente = normalizada.get(campo_canonico, '')
        if valor_existente and not valor_limpo:
            continue
        if valor_existente and valor_limpo:
            continue

        normalizada[campo_canonico] = valor_limpo

    # Espelha canônicos principais para compatibilidade com consumidores legados.
    if normalizada.get('setor') and not normalizada.get('departamento'):
        normalizada['departamento'] = normalizada['setor']
    if normalizada.get('tipo_ativo') and not normalizada.get('tipo'):
        normalizada['tipo'] = normalizada['tipo_ativo']

    return normalizada


class TipoErro(Enum):
    """Tipos de erro que causam rejeição de linha"""
    CAMPO_CRITICO_VAZIO = "campo_critico_vazio"
    DATA_INVALIDA = "data_invalida"
    TIPO_INVALIDO = "tipo_invalido"
    ID_INVALIDO = "id_invalido"
    VALOR_EXCEDE_COMPRIMENTO = "valor_excede_comprimento"
    EMAIL_INVALIDO = "email_invalido"
    ID_DUPLICADO_CSV = "id_duplicado_csv"
    NUMERO_INVALIDO = "numero_invalido"


class TipoAviso(Enum):
    """Tipos de aviso que não causam rejeição"""
    EMAIL_AUSENTE = "email_ausente"
    USUARIO_RESPONSAVEL_NAO_EXISTE = "usuario_responsavel_nao_existe"
    DATA_FUTURA = "data_futura"
    SERIAL_AUSENTE = "serial_ausente"
    MAPEAMENTO_BAIXA_CONFIANCA = "mapeamento_baixa_confianca"
    COLUNA_IGNORADA = "coluna_ignorada"
    # NOVO: Campo recomendável ausente gera aviso, não erro
    CAMPO_RECOMENDAVEL_AUSENTE = "campo_recomendavel_ausente"


@dataclass
class ResultadoValidacao:
    """Resultado da validação de uma linha"""
    valida: bool                              # True se sem erros
    erros: List[Tuple[TipoErro, str]]        # [(TipoErro, mensagem), ...]
    avisos: List[Tuple[TipoAviso, str]]      # [(TipoAviso, mensagem), ...]
    id_ativo: Optional[str] = None            # ID extraído (para duplicata)
    dados_limpos: Optional[Dict] = None       # Dados após limpeza


@dataclass
class ResultadoValidacaoLote:
    """Resultado da validação completa do lote"""
    total_linhas: int
    linhas_validas: int
    linhas_com_erro: int
    linhas_com_aviso: int
    taxa_erro_percentual: float
    bloqueios: List[str]                      # Bloqueios críticos
    alertas: List[str]                        # Alertas (permitem importação)
    validacoes_por_linha: List[ResultadoValidacao]


class ValidadorCampos:
    """Valida campos individuais contra regras de tipo e integridade"""

    # ===== NOVA CLASSIFICAÇÃO DE CRITICIDADE (Camada 2 — Flexibilização) =====
    # CAMPOS_BLOQUEANTES: Único que bloqueia a importação se ausente (TipoErro)
    # CAMPOS_RECOMENDAVEIS: Ausentes geram aviso (TipoAviso), não erro — permitem importação
    # CAMPOS_CRITICOS: Mantido para compatibilidade (união dos dois)

    # Campos que realmente bloqueiam se não mapeados
    CAMPOS_BLOQUEANTES = {
        'tipo_ativo', 'marca', 'modelo'
    }

    # Campos que geram aviso se ausentes, mas não bloqueiam
    CAMPOS_RECOMENDAVEIS = {
        'setor', 'status', 'data_entrada'
    }

    # Compatibilidade: union de bloqueantes + recomendáveis
    CAMPOS_CRITICOS = CAMPOS_BLOQUEANTES | CAMPOS_RECOMENDAVEIS

    # Comprimentos máximos — usar APENAS nomes canônicos (devem coincidir com schema.sql)
    # Removidas entradas antigas: 'tipo' (substituído por 'tipo_ativo'), 'departamento' (substituído por 'setor')
    COMPRIMENTOS_MAXIMOS = {
        'id': 20,
        'marca': 100,
        'modelo': 100,
        'serial': 120,
        'categoria': 100,
        'tipo_ativo': 50,
        'condicao': 50,
        'localizacao': 120,
        'setor': 100,
        'usuario_responsavel': 100,
        'email_responsavel': 255,
        'nota_fiscal': 100,
        'garantia': 100,
        'status': 50,
        'descricao': 255,
        'observacoes': 65535,  # TEXT
    }

    # Valores válidos para campos enumerados
    # Fonte única: usa o domínio oficial do backend para evitar divergência
    # entre validação de preview e validação final.
    STATUS_VALIDOS = set(STATUS_VALIDOS_DOMINIO)

    # Regex para validação
    REGEX_ID = re.compile(r'^[A-Za-z0-9\-]{1,20}$')  # Alfanumérico + hífen
    REGEX_EMAIL = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    REGEX_DATA_ISO = re.compile(r'^\d{4}-\d{2}-\d{2}$')

    @staticmethod
    def validar_campo_critico(nome_campo: str, valor: str) -> Optional[Tuple[TipoErro, str]]:
        """
        Valida se campo crítico está preenchido.
        Retorna (TipoErro, mensagem) se inválido, None se OK.
        """
        if not valor or not str(valor).strip():
            return (TipoErro.CAMPO_CRITICO_VAZIO, f"Campo obrigatório '{nome_campo}' está vazio")
        return None

    @staticmethod
    def validar_id(valor: str) -> Optional[Tuple[TipoErro, str]]:
        """
        Valida ID do ativo: alfanumérico + hífen, max 20 chars.
        """
        if not valor:
            return (TipoErro.CAMPO_CRITICO_VAZIO, "ID não pode estar vazio")

        valor = str(valor).strip()

        if len(valor) > 20:
            return (TipoErro.VALOR_EXCEDE_COMPRIMENTO, f"ID '{valor}' tem {len(valor)} chars (máx 20)")

        if not ValidadorCampos.REGEX_ID.match(valor):
            return (TipoErro.ID_INVALIDO, f"ID '{valor}' contém caracteres inválidos. Use: A-Z, 0-9, hífen")

        return None

    @staticmethod
    def validar_data(valor: str, campo_nome: str = "data") -> Optional[Tuple[TipoErro | TipoAviso, str]]:
        """
        Valida data em formato ISO 8601 (YYYY-MM-DD).
        Retorna erro se inválida, aviso se futura.
        """
        if not valor or not str(valor).strip():
            return None  # Data opcional

        valor = str(valor).strip()

        # Verificar formato
        if not ValidadorCampos.REGEX_DATA_ISO.match(valor):
            return (TipoErro.DATA_INVALIDA, f"{campo_nome} em formato inválido: '{valor}' (use YYYY-MM-DD)")

        try:
            data_obj = datetime.strptime(valor, '%Y-%m-%d').date()
        except ValueError:
            return (TipoErro.DATA_INVALIDA, f"{campo_nome} inválida: '{valor}' (ex: 2026-04-22 é inválida)")

        # Alertar se futura
        hoje = date.today()
        if data_obj > hoje and campo_nome == 'data_entrada':
            return (TipoAviso.DATA_FUTURA, f"{campo_nome} é futura ({valor})")

        return None

    @staticmethod
    def validar_email(valor: str) -> Optional[Tuple[TipoErro | TipoAviso, str]]:
        """
        Valida email. Se vazio, aviso. Se inválido, erro.
        """
        if not valor or not str(valor).strip():
            return (TipoAviso.EMAIL_AUSENTE, "Email não fornecido")

        valor = str(valor).strip()

        if not ValidadorCampos.REGEX_EMAIL.match(valor):
            return (TipoErro.EMAIL_INVALIDO, f"Email inválido: '{valor}'")

        return None

    @staticmethod
    def validar_numero(valor: str, campo_nome: str, decimais: int = 0) -> Optional[Tuple[TipoErro, str]]:
        """
        Valida número com casas decimais opcionais.
        """
        if not valor or not str(valor).strip():
            return None  # Opcional

        valor = str(valor).strip()

        try:
            num = float(valor)
            if num < 0:
                return (TipoErro.NUMERO_INVALIDO, f"{campo_nome} não pode ser negativo: {valor}")
        except ValueError:
            return (TipoErro.NUMERO_INVALIDO, f"{campo_nome} inválido (esperado número): {valor}")

        return None

    @staticmethod
    def validar_comprimento(valor: str, campo_nome: str, max_chars: int) -> Optional[Tuple[TipoErro, str]]:
        """
        Valida comprimento do campo contra limite do banco.
        """
        if not valor:
            return None

        valor_str = str(valor).strip()
        if len(valor_str) > max_chars:
            return (
                TipoErro.VALOR_EXCEDE_COMPRIMENTO,
                f"Campo '{campo_nome}' tem {len(valor_str)} chars (máx {max_chars})"
            )

        return None

    @staticmethod
    def validar_enum(valor: str, campo_nome: str, valores_validos: set) -> Optional[Tuple[TipoErro, str]]:
        """
        Valida que valor está em conjunto de valores válidos.
        """
        if not valor:
            return None

        valor = str(valor).strip()
        if valor not in valores_validos:
            return (
                TipoErro.TIPO_INVALIDO,
                f"Campo '{campo_nome}' = '{valor}' inválido. Valores válidos: {', '.join(valores_validos)}"
            )

        return None


class ValidadorLinha:
    """Valida linha completa de CSV"""

    def __init__(self):
        self.validador_campos = ValidadorCampos()

    def validar(
        self,
        linha: Dict[str, str],
        numero_linha: int,
        usuarios_existentes_cache: set = None,
        ativos_existentes_cache: set = None
    ) -> ResultadoValidacao:
        """
        Valida linha completa.

        Args:
            linha: Dicionário com dados da linha
            numero_linha: Número da linha no arquivo (para logging)
            usuarios_existentes_cache: Set de usuarios_responsavel válidos (para aviso)
            ativos_existentes_cache: Set de IDs de ativos já existentes (para aviso)

        Returns:
            ResultadoValidacao com erros, avisos e dados limpos
        """
        erros = []
        avisos = []
        dados_limpos = {}
        id_ativo = None

        # Consolida aliases em campos canônicos antes de aplicar regras.
        # Isso evita conflito entre setor/departamento e tipo/tipo_ativo na mesma linha.
        linha = normalizar_dados_importacao(linha)

        # ===== VALIDAR CAMPO ID (opcional no preview/import) =====
        # Se ID vier preenchido no CSV, validamos formato.
        # Se não vier, não bloqueia: o ID pode ser gerado automaticamente no INSERT.
        id_valor = linha.get('id', '').strip() if linha.get('id') else ''
        if id_valor:
            erro = self.validador_campos.validar_id(id_valor)
            if erro:
                erros.append(erro)
            else:
                id_ativo = id_valor
                dados_limpos['id'] = id_ativo

        # ===== VALIDAR CAMPOS BLOQUEANTES (geram erro se vazios) =====
        # (Camada 2: Flexibilização — apenas tipo_ativo, marca, modelo bloqueiam)
        for campo in ValidadorCampos.CAMPOS_BLOQUEANTES:
            valor = linha.get(campo, '').strip() if linha.get(campo) else ''
            erro = self.validador_campos.validar_campo_critico(campo, valor)
            if erro:
                erros.append(erro)
            else:
                dados_limpos[campo] = valor

        # ===== VALIDAR CAMPOS RECOMENDÁVEIS (geram aviso se vazios) =====
        # (Camada 2: Flexibilização — setor, status, data_entrada geram avisos, não erros)
        for campo in ValidadorCampos.CAMPOS_RECOMENDAVEIS:
            valor = linha.get(campo, '').strip() if linha.get(campo) else ''
            if not valor:
                # Campo vazio → aviso, não erro
                avisos.append((
                    TipoAviso.CAMPO_RECOMENDAVEL_AUSENTE,
                    f"Campo recomendável '{campo}' está vazio"
                ))
            else:
                dados_limpos[campo] = valor

        # ===== VALIDAR STATUS (enum) =====
        status = linha.get('status', '').strip() if linha.get('status') else ''
        if status:
            erro = self.validador_campos.validar_enum(
                status,
                'status',
                ValidadorCampos.STATUS_VALIDOS
            )
            if erro:
                erros.append(erro)
            else:
                dados_limpos['status'] = status

        # ===== VALIDAR DATAS =====
        for campo_data in ['data_entrada', 'data_saida', 'data_compra']:
            valor = linha.get(campo_data)
            if valor:
                result = self.validador_campos.validar_data(valor, campo_data)
                if result:
                    if result[0] == TipoErro.DATA_INVALIDA:
                        erros.append(result)
                    else:
                        avisos.append(result)
                else:
                    dados_limpos[campo_data] = valor.strip()

        # ===== VALIDAR EMAIL =====
        email = linha.get('email_responsavel')
        if email:
            result = self.validador_campos.validar_email(email)
            if result:
                if result[0] == TipoErro.EMAIL_INVALIDO:
                    erros.append(result)
                else:
                    avisos.append(result)
            else:
                dados_limpos['email_responsavel'] = email.strip()
        else:
            avisos.append((TipoAviso.EMAIL_AUSENTE, "Email não fornecido"))

        # ===== VALIDAR VALOR (numérico) =====
        valor = linha.get('valor')
        if valor:
            erro = self.validador_campos.validar_numero(valor, 'valor')
            if erro:
                erros.append(erro)
            else:
                dados_limpos['valor'] = float(valor)

        # ===== VALIDAR COMPRIMENTOS =====
        for campo, max_chars in ValidadorCampos.COMPRIMENTOS_MAXIMOS.items():
            valor = linha.get(campo)
            if valor:
                erro = self.validador_campos.validar_comprimento(valor, campo, max_chars)
                if erro:
                    erros.append(erro)

        # ===== VALIDAR USUARIO_RESPONSAVEL (aviso se não existe) =====
        usuario_responsavel = linha.get('usuario_responsavel')
        if usuario_responsavel and usuarios_existentes_cache:
            if usuario_responsavel.strip() not in usuarios_existentes_cache:
                avisos.append((
                    TipoAviso.USUARIO_RESPONSAVEL_NAO_EXISTE,
                    f"Usuário responsável '{usuario_responsavel}' não existe"
                ))

        # ===== VALIDAR SERIAL (aviso se duplicada) =====
        serial = linha.get('serial')
        if not serial:
            avisos.append((TipoAviso.SERIAL_AUSENTE, "Serial não fornecido"))
        elif ativos_existentes_cache and serial.strip() in ativos_existentes_cache:
            avisos.append((
                TipoAviso.SERIAL_AUSENTE,  # Reusing enum, but meaning "duplicate serial"
                f"Serial '{serial}' já existe"
            ))

        return ResultadoValidacao(
            valida=len(erros) == 0,
            erros=erros,
            avisos=avisos,
            id_ativo=id_ativo,
            dados_limpos=dados_limpos
        )


class ValidadorLote:
    """Valida lote completo e emite bloqueios/alertas"""

    def __init__(self):
        self.validador_linha = ValidadorLinha()

    def validar_lote(
        self,
        linhas: List[Dict[str, str]],
        mapeamento_campos: Dict[str, Tuple[str, float]],
        usuarios_existentes: set = None,
        ativos_existentes: set = None
    ) -> ResultadoValidacaoLote:
        """
        Valida lote completo.

        Args:
            linhas: Lista de dicionários (uma por linha CSV)
            mapeamento_campos: {coluna_csv: (campo_banco, score_confianca)}
            usuarios_existentes: Set de usuarios válidos (cache)
            ativos_existentes: Set de IDs já existentes (cache)

        Returns:
            ResultadoValidacaoLote com status geral e bloqueios
        """
        validacoes = []
        ids_vistos = set()
        bloqueios = []
        alertas = []

        # 1. Validar cada linha
        for i, linha in enumerate(linhas, start=1):
            resultado = self.validador_linha.validar(
                linha,
                i,
                usuarios_existentes,
                ativos_existentes
            )
            validacoes.append(resultado)

            # Detectar ID duplicado dentro do CSV
            if resultado.id_ativo:
                if resultado.id_ativo in ids_vistos:
                    resultado.erros.append((
                        TipoErro.ID_DUPLICADO_CSV,
                        f"ID '{resultado.id_ativo}' aparece mais de uma vez"
                    ))
                    resultado.valida = False
                else:
                    ids_vistos.add(resultado.id_ativo)

        # 2. Calcular taxa de erro
        linhas_com_erro = sum(1 for v in validacoes if not v.valida)
        linhas_com_aviso = sum(1 for v in validacoes if v.avisos and v.valida)
        linhas_validas = len(validacoes) - linhas_com_erro

        taxa_erro = (linhas_com_erro / len(validacoes) * 100) if validacoes else 0

        # 3. Emitir bloqueios (críticos)
        if taxa_erro > 50:
            bloqueios.append(
                f"Taxa de erro > 50% ({linhas_com_erro}/{len(validacoes)} linhas)"
            )

        # 4. Verificar campos bloqueantes mapeados (Camada 2: apenas bloqueantes bloqueiam)
        # IMPORTANTE: Contrato de mapeamento_campos = {coluna_origem: (campo_destino, score)}
        # Devemos acumular os CAMPOS DESTINO (canônicos) que estão em CAMPOS_BLOQUEANTES
        # Não colunas de origem, que seria um tipo de dados diferente
        campos_destino_mapeados = {
            normalizar_campo_importacao(campo)
            for coluna, (campo, score) in mapeamento_campos.items()
            if campo and normalizar_campo_importacao(campo) in ValidadorCampos.CAMPOS_BLOQUEANTES
        }

        # Campos bloqueantes que NÃO foram mapeados a nenhuma coluna
        campos_bloqueantes_faltantes = (
            ValidadorCampos.CAMPOS_BLOQUEANTES - campos_destino_mapeados
        )

        if campos_bloqueantes_faltantes:
            bloqueios.append(
                f"Campos obrigatórios não mapeados: {', '.join(sorted(campos_bloqueantes_faltantes))}"
            )

        # 4b. Verificar campos recomendáveis mapeados (geram alerta, não bloqueio)
        campos_recomendaveis_mapeados = {
            normalizar_campo_importacao(campo)
            for coluna, (campo, score) in mapeamento_campos.items()
            if campo and normalizar_campo_importacao(campo) in ValidadorCampos.CAMPOS_RECOMENDAVEIS
        }

        campos_recomendaveis_faltantes = (
            ValidadorCampos.CAMPOS_RECOMENDAVEIS - campos_recomendaveis_mapeados
        )

        if campos_recomendaveis_faltantes:
            alertas.append(
                f"Campos recomendáveis não mapeados (gerarão avisos): {', '.join(sorted(campos_recomendaveis_faltantes))}"
            )

        # 5. Verificar mapeamentos com baixa confiança
        mapeamentos_baixa_confianca = [
            (coluna, score) for coluna, (campo, score) in mapeamento_campos.items()
            if score < 0.6
        ]

        if mapeamentos_baixa_confianca:
            alertas.append(
                f"Mapeamentos com baixa confiança: {len(mapeamentos_baixa_confianca)}"
            )

        return ResultadoValidacaoLote(
            total_linhas=len(validacoes),
            linhas_validas=linhas_validas,
            linhas_com_erro=linhas_com_erro,
            linhas_com_aviso=linhas_com_aviso,
            taxa_erro_percentual=taxa_erro,
            bloqueios=bloqueios,
            alertas=alertas,
            validacoes_por_linha=validacoes
        )


def classificar_status_importacao(
    taxa_erro: float,
    bloqueios: List[str],
    avisos: List[str]
) -> Tuple[str, str]:
    """
    Classifica o status geral da importação.

    Returns:
        (status, cor_indicador)
        status: "seguro" | "alerta" | "bloqueado"
        cor: "green" | "yellow" | "red"
    """
    if bloqueios:
        return ("bloqueado", "red")

    if taxa_erro > 10 or avisos:
        return ("alerta", "yellow")

    return ("seguro", "green")
