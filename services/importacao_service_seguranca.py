# services/importacao_service_seguranca.py
#
# Extensão de segurança operacional para importação.
# Integra validadores, auditoria e bloqueios corporativos.
#
# Nota: Este módulo é uma camada adicional que enriquece
# importacao_service.py sem modificar código existente (zero breaking changes).
#

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from types import SimpleNamespace

from services.importacao_service import ServicoImportacao
from services.auditoria_importacao_service import AuditoriaImportacaoService
from utils.import_validators import (
    ValidadorLote,
    classificar_status_importacao,
)
from utils.email_inference import aplicar_inferencia_email_em_dados
from utils.import_mapper import ResultadoMatch
from utils.import_schema import CRITICIDADE_CAMPOS  # Para campos_destino_disponiveis

logger = logging.getLogger(__name__)


class ServicoImportacaoComSeguranca:
    """
    Estende ServicoImportacao com validação, auditoria e bloqueios de segurança.

    Responsabilidades adicionais:
    - Validar dados de cada linha (tipo, comprimento, enum, datas, etc)
    - Detectar duplicatas (ID + serial)
    - Emitir bloqueios críticos (campo faltando, taxa erro > 50%, etc)
    - Registrar auditoria completa de importação
    - Registrar bloqueios e avisos por linha

    Uso:
        servico = ServicoImportacaoComSeguranca()
        id_lote, preview = servico.gerar_preview_seguro(
            conteudo_csv,
            usuario_id=1,
            empresa_id=5,
            endereco_ip="192.168.1.100",
            user_agent="Mozilla/5.0..."
        )
    """

    def __init__(self):
        """Inicializa serviços componentes"""
        self.servico_base = ServicoImportacao()
        self.validador_lote = ValidadorLote()

    def gerar_preview_seguro(
        self,
        conteudo_csv: bytes,
        usuario_id: int,
        empresa_id: int,
        endereco_ip: str,
        user_agent: str,
        delimitador: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        Gera preview com validação completa e auditoria.

        Args:
            conteudo_csv: Arquivo CSV como bytes
            usuario_id: ID do usuário
            empresa_id: ID da empresa
            endereco_ip: IP da requisição
            user_agent: User-Agent do navegador
            delimitador: Delimitador opcional

        Returns:
            (id_lote, preview_dict)

        Raises:
            ValueError se arquivo inválido
        """
        # 1. Processar arquivo (código base existente)
        headers_originais, linhas, metadados = self.servico_base.processar_arquivo_csv(
            conteudo_csv, delimitador
        )

        # 2. Fazer mapeamento (código base existente)
        resultado_mapeamento = self.servico_base.fazer_mapeamento(headers_originais)
        resultado_mapeamento.metadados = metadados

        # 3. Iniciar auditoria (com total de linhas do arquivo)
        total_linhas = len(linhas)
        id_lote = AuditoriaImportacaoService.iniciar_auditoria(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            hash_arquivo=metadados.hash_arquivo,
            nome_arquivo="upload.csv",  # Melhoria: passar como parâmetro na requisição
            tamanho_bytes=len(conteudo_csv),
            endereco_ip=endereco_ip,
            user_agent=user_agent,
            total_linhas=total_linhas
        )

        # 4. Converter linhas para formato de validação
        linhas_dict = []
        inferencia_por_linha = {}
        for _numero_linha, row in linhas:
            # Mapear usando resultado_mapeamento.matches
            linha_mapeada = self._mapear_linha(row, resultado_mapeamento.matches)
            # Aplica inferencia backend antes da validacao para que a pre-visualizacao
            # reflita os dados revisados que serao usados na confirmacao final.
            linha_revisada, metadados_inferencia = aplicar_inferencia_email_em_dados(linha_mapeada)
            linhas_dict.append(linha_revisada)
            inferencia_por_linha[_numero_linha] = metadados_inferencia

        # 5. Validar lote (com detectores de duplicata)
        usuarios_cache = AuditoriaImportacaoService.obter_usuarios_validos(empresa_id)

        ids_csv = [l.get('id') for l in linhas_dict if l.get('id')]
        duplicatas_ids = AuditoriaImportacaoService.detectar_duplicatas(ids_csv, empresa_id)

        seriais_csv = [l.get('serial') for l in linhas_dict if l.get('serial')]
        duplicatas_seriais = AuditoriaImportacaoService.detectar_seriais_duplicados(
            seriais_csv, empresa_id
        )

        # Construir mapeamento de colunas com validação defensiva do contrato de ResultadoMatch
        # Contrato: cada match DEVE ter coluna_origem (nome da coluna no CSV)
        # Tipo esperado: Dict[str, Tuple[str, float]] = {coluna_csv: (campo_banco, score)}
        mapeamento_campos = {}
        for m in resultado_mapeamento.matches:
            if not m.campo_destino:
                continue
            # Validação: garantir que match tem os atributos esperados
            if not hasattr(m, 'coluna_origem'):
                logger.error(
                    "CONTRATO VIOLADO ao construir mapeamento_campos: "
                    "ResultadoMatch sem 'coluna_origem'. Tipo: %s. Atributos: %s",
                    type(m).__name__,
                    [attr for attr in dir(m) if not attr.startswith('_')]
                )
                raise AttributeError(
                    f"ResultadoMatch deve ter 'coluna_origem' "
                    f"(tipo recebido: {type(m).__name__}). "
                    f"Verifique a definição em utils/import_mapper.py"
                )
            mapeamento_campos[m.coluna_origem] = (m.campo_destino, m.score)

        validacao_lote = self.validador_lote.validar_lote(
            linhas=linhas_dict,
            mapeamento_campos=mapeamento_campos,
            usuarios_existentes=usuarios_cache,
            ativos_existentes=set(duplicatas_ids.keys())
        )

        # ===== BUG FIX 1: Extrair erros e avisos reais por linha =====
        # O validador_lote retorna validacoes_por_linha com dados reais de cada linha.
        # Precisamos extrair isso para a UI em vez de herdar erros_por_linha vazios do preview_base.
        erros_por_linha_seguro = []
        avisos_por_linha_seguro = []
        for idx, validacao in enumerate(validacao_lote.validacoes_por_linha):
            numero_linha = linhas[idx][0] if idx < len(linhas) else idx + 2
            if validacao.erros:
                # Cada erro é tupla (TipoErro, mensagem_str)
                erros_por_linha_seguro.append({
                    "linha": numero_linha,
                    "mensagem": validacao.erros[0][1],  # Primeira mensagem
                    "erros": [
                        {"tipo": e[0].name, "mensagem": e[1]}
                        for e in validacao.erros
                    ],
                })
            if validacao.avisos:
                # Cada aviso é tupla (TipoAviso, mensagem_str)
                avisos_por_linha_seguro.append({
                    "linha": numero_linha,
                    "mensagens": [a[1] for a in validacao.avisos],
                })

        # ===== BUG FIX 2: Construir amostra com dados mapeados =====
        # O frontend lê preview_linhas[].dados_mapeados (nunca existe).
        # Aqui construímos amostra com dados já convertidos para campos canônicos.
        amostra_gravacao = [
            {"linha": linhas[i][0], "dados_mapeados": linhas_dict[i]}
            for i in range(min(5, len(linhas)))
        ]

        # ===== NOVO (Camada 4): Construir linhas_revisao completo para grade de revisão =====
        # (Camada 2 — Central de Revisão: todas as linhas com status, erros, avisos para edição/descarte)
        linhas_revisao = []
        for i, (numero_linha, row) in enumerate(linhas):
            # Comentário: Validar que validacao_por_linha[i] existe (contrato: uma validação por linha)
            # Se não existir, usar validação default (valid=True, sem erros)
            if i < len(validacao_lote.validacoes_por_linha):
                validacao = validacao_lote.validacoes_por_linha[i]
            else:
                # Fallback: linha não foi validada (comportamento defensivo)
                validacao = SimpleNamespace(
                    valida=True,
                    erros=[],
                    avisos=[],
                    id_ativo=None,
                )
            linhas_revisao.append({
                "linha": numero_linha,
                # Dados originais do CSV (para referência)
                "dados_originais": dict(row),
                # Snapshot mapeado antes da inferencia para rastrear origem dos valores.
                "dados_mapeados_originais": self._mapear_linha(row, resultado_mapeamento.matches),
                # Dados após mapeamento (prontos para persistência)
                "dados_mapeados": linhas_dict[i],
                # Status de validação
                "valida": validacao.valida,
                "tem_erro": len(validacao.erros) > 0,
                "tem_aviso": len(validacao.avisos) > 0 and len(validacao.erros) == 0,
                # Metadados da inferencia por e-mail para confirmacao assistida na UI.
                "inferencia_email": inferencia_por_linha.get(numero_linha, {}),
                # Erros e avisos estruturados (para exibição)
                "erros": [
                    {"tipo": e[0].name, "mensagem": e[1]}
                    for e in validacao.erros
                ],
                "avisos": [
                    {"tipo": a[0].name, "mensagem": a[1]}
                    for a in validacao.avisos
                ],
            })

        # 6. Classificar status
        status_risco, cor = classificar_status_importacao(
            validacao_lote.taxa_erro_percentual,
            validacao_lote.bloqueios,
            validacao_lote.alertas
        )

        # 7. Registrar preview em auditoria
        AuditoriaImportacaoService.registrar_preview_gerado(
            id_lote=id_lote,
            delimitador=metadados.delimitador,
            numero_linha_cabecalho=metadados.numero_linha_cabecalho,
            score_deteccao_cabecalho=metadados.score_deteccao_cabecalho,
            total_linhas=len(linhas),
            dados_bloqueios=validacao_lote.bloqueios,
            dados_avisos=validacao_lote.alertas
        )

        # 8. Gerar preview base (código existente)
        preview_base = self.servico_base.gerar_preview_estruturado(
            resultado_mapeamento,
            primeiras_linhas=linhas[:5],
            max_linhas_preview=5
        )

        # 9. Enriquecer preview com dados de segurança
        preview_enriquecido = {
            **preview_base,  # Mantém tudo antigo

            # Novos campos de segurança
            "indicador_risco": {
                "status": status_risco,
                "cor": cor,
                "bloqueios": validacao_lote.bloqueios,
                "alertas": validacao_lote.alertas
            },

            "validacao_detalhes": {
                "total_linhas": validacao_lote.total_linhas,
                "linhas_validas": validacao_lote.linhas_validas,
                "linhas_com_erro": validacao_lote.linhas_com_erro,
                "linhas_invalidas": validacao_lote.linhas_com_erro,
                "linhas_com_aviso": validacao_lote.linhas_com_aviso,
                "taxa_erro_percentual": round(validacao_lote.taxa_erro_percentual, 2)
            },

            "duplicatas_detectadas": {
                "ids_existentes": list(duplicatas_ids.keys()),
                "seriais_duplicados": list(duplicatas_seriais.keys())
            },

            "metadados_auditoria": {
                "id_lote": id_lote,
                "hash_arquivo": metadados.hash_arquivo,
                "timestamp_preview": datetime.utcnow().isoformat()
            }
        }

        # Compatibilidade explícita com a tela: algumas versões do frontend leem
        # resumo_analise antes de validacao_detalhes/resumo_validacao.
        # Mantemos o mesmo conteúdo para evitar contadores zerados na UI.
        preview_enriquecido["resumo_analise"] = {
            "total_linhas": validacao_lote.total_linhas,
            "linhas_validas": validacao_lote.linhas_validas,
            "linhas_invalidas": validacao_lote.linhas_com_erro,
            "colunas_reconhecidas_automaticamente": len(preview_base.get("colunas", {}).get("exatas", [])),
            "colunas_sugeridas": len(preview_base.get("colunas", {}).get("sugeridas", [])),
            "colunas_ignoradas": len(preview_base.get("colunas", {}).get("ignoradas", [])),
            "campos_obrigatorios_nao_reconhecidos": len(preview_base.get("campos_obrigatorios_nao_reconhecidos", [])),
        }

        # ===== BUG FIX 1 & 2: Sobrescrever campos com dados corretos do validador =====
        # O preview_base herda erros_por_linha vazios (preview_base não valida linhas).
        # Sobrescrevemos com dados reais extraídos de validacoes_por_linha acima.
        preview_enriquecido["erros_por_linha"] = erros_por_linha_seguro
        preview_enriquecido["avisos_por_linha"] = avisos_por_linha_seguro
        preview_enriquecido["preview_linhas"] = amostra_gravacao
        preview_enriquecido["campos_destino_disponiveis"] = sorted(list(CRITICIDADE_CAMPOS.keys()))

        # ===== NOVO (Camada 4): Adicionar linhas_revisao completo ao preview =====
        # Grade de revisão contém TODAS as linhas para que o usuário possa editar/descartar
        preview_enriquecido["linhas_revisao"] = linhas_revisao

        logger.info(
            "importacao.preview_seguro id_lote=%s total_linhas=%s validas=%s invalidas=%s exatas=%s sugeridas=%s bloqueios=%s",
            id_lote,
            validacao_lote.total_linhas,
            validacao_lote.linhas_validas,
            validacao_lote.linhas_com_erro,
            len(preview_base.get("colunas", {}).get("exatas", [])),
            len(preview_base.get("colunas", {}).get("sugeridas", [])),
            len(validacao_lote.bloqueios),
        )

        return id_lote, preview_enriquecido

    def registrar_linha_importada(
        self,
        id_lote: str,
        numero_linha: int,
        id_ativo_csv: str,
        id_ativo_criado: str,
        operacao: str,  # 'INSERT' ou 'UPDATE'
        avisos: Optional[List[str]] = None
    ) -> None:
        """Registra linha que foi importada com sucesso"""
        AuditoriaImportacaoService.registrar_linha_importada(
            id_lote=id_lote,
            numero_linha=numero_linha,
            id_ativo_csv=id_ativo_csv,
            id_ativo_criado=id_ativo_criado,
            operacao=operacao,
            avisos=avisos
        )

    def registrar_linha_rejeitada(
        self,
        id_lote: str,
        numero_linha: int,
        id_ativo_csv: Optional[str],
        motivo: str,
        avisos: Optional[List] = None,
        campos_processados: Optional[Dict] = None
    ) -> None:
        """Registra linha que foi rejeitada"""
        AuditoriaImportacaoService.registrar_linha_rejeitada(
            id_lote=id_lote,
            numero_linha=numero_linha,
            id_ativo_csv=id_ativo_csv,
            motivo=motivo,
            avisos=avisos,
            campos_processados=campos_processados
        )

    def registrar_resultado_final(
        self,
        id_lote: str,
        linhas_importadas: int,
        linhas_rejeitadas: int,
        linhas_com_aviso: int,
        linhas_atualizadas: int,
        ids_ativos_afetados: List[str],
        mensagem_erro: Optional[str] = None
    ) -> None:
        """Registra resultado final da importação"""
        AuditoriaImportacaoService.registrar_resultado_importacao(
            id_lote=id_lote,
            linhas_importadas=linhas_importadas,
            linhas_rejeitadas=linhas_rejeitadas,
            linhas_com_aviso=linhas_com_aviso,
            linhas_atualizadas=linhas_atualizadas,
            ids_ativos_afetados=ids_ativos_afetados,
            mensagem_erro=mensagem_erro
        )

    @staticmethod
    def _mapear_linha(
        row: Dict[str, str],
        matches: List[ResultadoMatch]
    ) -> Dict[str, str]:
        """
        Mapeia linha original (chaves originais do CSV) para campos de banco.

        Contrato obrigatório:
        - row: dicionário com chaves = nomes originais de colunas do CSV
        - matches: List[ResultadoMatch] onde cada match tem:
            - coluna_origem: str (chave no `row`)
            - campo_destino: Optional[str] (nome do campo no banco)
            - score: float (confiança 0.0-1.0)
            - deve_ignorar: bool (True se score < limiar)

        Uso:
            Cada ResultadoMatch instrui como mapear uma coluna original
            para um campo de banco. Colunas ignoradas ou sem mapeamento
            são puladas.

        Raises:
            AttributeError: Se match não tiver coluna_origem (indicando
                           contrato violado ou versão desatualizada de ResultadoMatch)
            KeyError: Nunca deve ocorrer (usa .get() defensivo)
        """
        linha_mapeada = {}

        for match in matches:
            # Validação defensiva: garante que match tem os atributos esperados
            if not hasattr(match, 'coluna_origem'):
                logger.error(
                    "CONTRATO VIOLADO: ResultadoMatch sem atributo 'coluna_origem'. "
                    "Tipo recebido: %s. Atributos: %s",
                    type(match).__name__,
                    dir(match)
                )
                raise AttributeError(
                    f"ResultadoMatch deve ter atributo 'coluna_origem' "
                    f"(tipo recebido: {type(match).__name__})"
                )

            # Pula colunas que não devem ser mapeadas
            if not match.campo_destino or match.deve_ignorar:
                continue

            # Extrai valor original com tratamento defensivo
            valor_original = row.get(match.coluna_origem, '').strip()

            # Aplica limpeza básica e mapeia para campo destino
            if valor_original:
                linha_mapeada[match.campo_destino] = valor_original

        return linha_mapeada
