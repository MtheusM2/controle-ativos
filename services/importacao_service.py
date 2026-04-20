# services/importacao_service.py
#
# Serviço de orquestração do novo motor de importação flexível.
# Coordena detecção de cabeçalho, matching de colunas e geração de preview estruturado.
#
# Responsabilidade:
# - Parsing robusto de arquivo (CSV, XLSX futura)
# - Detecção automática de cabeçalho
# - Matching de colunas com scores
# - Construção de preview com rastreabilidade
# - NÃO acessa banco de dados (responsabilidade do service principal)
# - NÃO valida regras de negócio (responsabilidade do validator)
#

import hashlib
import io
import csv
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from utils.import_schema import (
    obter_campos_criticos,
    obter_campos_com_inferencia,
    obter_criticidade_campo,
    CRITICIDADE_CAMPOS,
    CriticalidadeCampo,
    LIMIAR_CONFIANCA_ALTA,
    LIMIAR_CONFIANCA_MEDIA,
    LIMIAR_CONFIANCA_BAIXA,
)
from utils.import_header_detector import DetectorCabecalho
from utils.import_mapper import MotorMatching, ResultadoMatch


@dataclass
class MetadadosArquivo:
    """
    Metadados de leitura do arquivo.
    """
    # Comentário: delimitador detectado ou inferido
    delimitador: str
    # Comentário: codificação usada (sempre UTF-8 normalizado)
    codificacao: str
    # Comentário: número de linha onde cabeçalho foi detectado (0-indexed)
    numero_linha_cabecalho: int
    # Comentário: score de confiança da detecção de cabeçalho (0.0–1.0)
    score_deteccao_cabecalho: float
    # Comentário: hash SHA256 do arquivo (para rastreabilidade)
    hash_arquivo: str


@dataclass
class ResultadoMapeamento:
    """
    Resultado de mapeamento de todas as colunas.
    """
    # Comentário: lista de matches (uma por coluna original)
    matches: List[ResultadoMatch]
    # Comentário: metadados de arquivo
    metadados: MetadadosArquivo
    # Comentário: campos críticos mapeados
    campos_criticos_mapeados: set
    # Comentário: campos críticos NÃO mapeados (bloqueiam importação)
    campos_criticos_faltantes: set
    # Comentário: campos com mapeamento de alta confiança
    mapeamentos_altos: List[ResultadoMatch]
    # Comentário: campos com mapeamento de média confiança
    mapeamentos_medios: List[ResultadoMatch]
    # Comentário: campos com mapeamento de baixa confiança
    mapeamentos_baixos: List[ResultadoMatch]
    # Comentário: campos ignorados (score abaixo do limiar)
    campos_ignorados: List[ResultadoMatch]
    # Comentário: colunas duplicadas (mapeadas para mesmo campo)
    duplicatas: Dict[str, List[ResultadoMatch]]


class ServicoImportacao:
    """
    Serviço central de importação com novo motor flexível.
    """

    def __init__(self):
        """Inicializa motor de reconhecimento."""
        # Comentário: inicializa componentes modulares
        self.detector_cabecalho = DetectorCabecalho()
        self.motor_matching = MotorMatching()
        self.campos_criticos = obter_campos_criticos()
        self.campos_com_inferencia = obter_campos_com_inferencia()

    def processar_arquivo_csv(
        self, conteudo_bytes: bytes, delimitador: Optional[str] = None
    ) -> Tuple[List[str], List[Tuple[int, dict]], MetadadosArquivo]:
        """
        Lê e processa arquivo CSV em memória.

        Args:
            conteudo_bytes: Arquivo como bytes
            delimitador: Delimitador explícito (ou None para detectar)

        Returns:
            Tupla (headers_normalizados, linhas, metadados)

        Raises:
            ValueError: Se arquivo for inválido
        """
        # Comentário: hash para rastreabilidade
        hash_arquivo = hashlib.sha256(conteudo_bytes).hexdigest()

        # ===== PASSO 1: Decodificação =====
        # Comentário: tenta UTF-8, que é padrão
        try:
            texto = conteudo_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            # Comentário: fallback para Latin-1 como last resort
            try:
                texto = conteudo_bytes.decode("latin-1")
            except UnicodeDecodeError as e:
                raise ValueError(
                    "Arquivo não pode ser decodificado. "
                    "Use codificação UTF-8 ou Latin-1."
                ) from e

        # ===== PASSO 2: Detectar Delimitador =====
        # Comentário: se não fornecido, tenta inferir
        if not delimitador:
            delimitador = self._detectar_delimitador(texto)

        # ===== PASSO 3: Ler Linhas =====
        stream = io.StringIO(texto, newline="")
        reader = csv.DictReader(stream, delimiter=delimitador)

        if not reader.fieldnames:
            raise ValueError("CSV vazio ou sem cabeçalho.")

        # Comentário: armazena nomes originais de cabeçalho (antes de normalizar)
        headers_originais = reader.fieldnames

        # ===== PASSO 4: Detectar Linha de Cabeçalho =====
        # Comentário: recarrega arquivo para detecção (se houver lixo acima)
        stream_raw = io.StringIO(texto, newline="")
        linhas_raw = [line.rstrip("\r\n") for line in stream_raw]

        try:
            numero_linha_cabecalho, headers_normalizados, score_deteccao = (
                self.detector_cabecalho.detectar_cabecalho(linhas_raw, delimitador)
            )
        except ValueError as e:
            # Comentário: se detecção automática falhar, usa primeira linha
            numero_linha_cabecalho = 0
            headers_normalizados = [h.lower().strip() for h in headers_originais]
            score_deteccao = 0.5
            # Nota: em UI, podemos oferecer seleção manual neste ponto

        # ===== PASSO 5: Ler Dados =====
        # Comentário: recarrega com cabeçalho definido
        stream_dados = io.StringIO(texto, newline="")
        reader_dados = csv.DictReader(stream_dados, delimiter=delimitador)
        linhas = []
        for numero_linha, row in enumerate(reader_dados, start=numero_linha_cabecalho + 2):
            # Comentário: limpa linha (trata None como string vazia, filtra chaves None)
            linha_limpa = {
                (k.strip() if isinstance(k, str) else ""): (v.strip() if isinstance(v, str) else "")
                for k, v in row.items()
                if k is not None  # Ignora chaves nulas (coluna mal formada)
            }
            # Comentário: pula linhas totalmente vazias
            if any(v for v in linha_limpa.values()):
                linhas.append((numero_linha, linha_limpa))

        if not linhas:
            raise ValueError("Arquivo sem linhas de dados para importação.")

        # ===== PASSO 6: Retorna Metadados =====
        metadados = MetadadosArquivo(
            delimitador=delimitador,
            codificacao="utf-8",
            numero_linha_cabecalho=numero_linha_cabecalho,
            score_deteccao_cabecalho=score_deteccao,
            hash_arquivo=hash_arquivo,
        )

        return headers_originais, linhas, metadados

    def fazer_mapeamento(
        self, headers_originais: List[str]
    ) -> ResultadoMapeamento:
        """
        Faz matching de headers contra schema com scores.

        Args:
            headers_originais: Lista de nomes de coluna originais

        Returns:
            ResultadoMapeamento com categorização completa
        """
        # Comentário: normaliza headers
        headers_norm = [h.lower().strip() for h in headers_originais]

        # Comentário: processa cabecalho com motor
        matches = self.motor_matching.processar_cabecalho(headers_norm)

        # ===== CATEGORIZA RESULTADOS =====
        mapeamentos_altos = []
        mapeamentos_medios = []
        mapeamentos_baixos = []
        campos_ignorados = []
        campos_criticos_mapeados = set()
        duplicatas: Dict[str, List[ResultadoMatch]] = {}

        for match in matches:
            # Comentário: categoriza por score
            if match.deve_ignorar:
                campos_ignorados.append(match)
            elif match.confianca_alta:
                mapeamentos_altos.append(match)
                if match.campo_destino in self.campos_criticos:
                    campos_criticos_mapeados.add(match.campo_destino)
            elif match.confianca_media:
                mapeamentos_medios.append(match)
                if match.campo_destino in self.campos_criticos:
                    campos_criticos_mapeados.add(match.campo_destino)
            elif match.confianca_baixa:
                mapeamentos_baixos.append(match)
                if match.campo_destino in self.campos_criticos:
                    campos_criticos_mapeados.add(match.campo_destino)

        # Comentário: detecta duplicatas
        campos_por_destino = {}
        for match in matches:
            if match.campo_destino:
                if match.campo_destino not in campos_por_destino:
                    campos_por_destino[match.campo_destino] = []
                campos_por_destino[match.campo_destino].append(match)

        duplicatas = {
            campo: lista
            for campo, lista in campos_por_destino.items()
            if len(lista) > 1
        }

        # Comentário: identifica campos críticos faltantes
        campos_criticos_faltantes = self.campos_criticos - campos_criticos_mapeados

        return ResultadoMapeamento(
            matches=matches,
            metadados=None,  # Preenchido depois pelo chamador
            campos_criticos_mapeados=campos_criticos_mapeados,
            campos_criticos_faltantes=campos_criticos_faltantes,
            mapeamentos_altos=mapeamentos_altos,
            mapeamentos_medios=mapeamentos_medios,
            mapeamentos_baixos=mapeamentos_baixos,
            campos_ignorados=campos_ignorados,
            duplicatas=duplicatas,
        )

    def _enriquecer_match_com_regra_bloqueio(self, match: ResultadoMatch) -> Dict:
        """
        Enriquece dados de match com informação sobre bloqueio/confirmação necessária.

        Returns:
            Dict com para_dict() + informações adicionais
        """
        dados = match.para_dict()

        if not match.campo_destino:
            # Comentário: campo ignorado
            dados["acao_esperada"] = "ignorar"
            dados["requer_confirmacao"] = False
            return dados

        # Comentário: obtém criticidade do campo
        criticidade = obter_criticidade_campo(match.campo_destino)

        # ===== LÓGICA DE BLOQUEIO E CONFIRMAÇÃO =====
        limiar_alta = LIMIAR_CONFIANCA_ALTA / 100.0
        limiar_media = LIMIAR_CONFIANCA_MEDIA / 100.0
        limiar_baixa = LIMIAR_CONFIANCA_BAIXA / 100.0

        if criticidade == CriticalidadeCampo.CRITICO:
            # Comentário: Campos críticos têm regras rígidas
            if match.score >= limiar_alta:
                dados["acao_esperada"] = "auto_aplicar"
                dados["requer_confirmacao"] = False
                dados["classe_checkbox"] = "high_confidence"
            elif match.score >= limiar_media:
                dados["acao_esperada"] = "sugerir_com_pre_selecao"
                dados["requer_confirmacao"] = True
                dados["classe_checkbox"] = "medium_confidence"
            else:
                # Comentário: score < 75% em campo crítico = BLOQUEIA
                dados["acao_esperada"] = "bloqueia_importacao"
                dados["requer_confirmacao"] = True
                dados["classe_checkbox"] = "blocklist"

        elif criticidade == CriticalidadeCampo.OBRIGATORIO_COM_INFERENCIA:
            # Comentário: Campos com fallback/inferência têm regras moderadas
            if match.score >= limiar_alta:
                dados["acao_esperada"] = "auto_aplicar"
                dados["requer_confirmacao"] = False
                dados["classe_checkbox"] = "high_confidence"
            elif match.score >= limiar_media:
                dados["acao_esperada"] = "sugerir_com_pre_selecao"
                dados["requer_confirmacao"] = True
                dados["classe_checkbox"] = "medium_confidence"
            elif match.score >= limiar_baixa:
                dados["acao_esperada"] = "sugerir_sem_pre_selecao"
                dados["requer_confirmacao"] = False
                dados["classe_checkbox"] = "low_confidence"
            else:
                dados["acao_esperada"] = "ignorar"
                dados["requer_confirmacao"] = False
                dados["classe_checkbox"] = "ignored"

        else:  # CriticalidadeCampo.OPCIONAL
            # Comentário: Campos opcionais têm regras flexíveis
            if match.score >= limiar_media:
                dados["acao_esperada"] = "auto_aplicar"
                dados["requer_confirmacao"] = False
                dados["classe_checkbox"] = "high_confidence"
            elif match.score >= limiar_baixa:
                dados["acao_esperada"] = "sugerir_sem_pre_selecao"
                dados["requer_confirmacao"] = False
                dados["classe_checkbox"] = "low_confidence"
            else:
                dados["acao_esperada"] = "ignorar"
                dados["requer_confirmacao"] = False
                dados["classe_checkbox"] = "ignored"

        return dados

    def gerar_preview_estruturado(
        self,
        resultado_mapeamento: ResultadoMapeamento,
        primeiras_linhas: Optional[List[Tuple[int, dict]]] = None,
        max_linhas_preview: int = 5,
    ) -> Dict:
        """
        Gera estrutura de preview para envio à UI com regras de bloqueio/confirmação.

        Args:
            resultado_mapeamento: Resultado do mapeamento
            primeiras_linhas: Amostra de linhas para preview (opcional)
            max_linhas_preview: Quantas linhas incluir no preview

        Returns:
            Dicionário estruturado com:
            - colunas (exatas, sugeridas, ignoradas com scores + ações esperadas)
            - preview de dados
            - resumo de validação com informações de bloqueio
            - avisos detalhados
        """
        # Comentário: prepara dados de colunas com ações esperadas
        colunas_preview = {
            "exatas": [
                self._enriquecer_match_com_regra_bloqueio(m)
                for m in resultado_mapeamento.mapeamentos_altos
            ],
            "sugeridas": [
                self._enriquecer_match_com_regra_bloqueio(m)
                for m in (
                    resultado_mapeamento.mapeamentos_medios
                    + resultado_mapeamento.mapeamentos_baixos
                )
            ],
            "ignoradas": [
                self._enriquecer_match_com_regra_bloqueio(m)
                for m in resultado_mapeamento.campos_ignorados
            ],
        }

        # Comentário: prepara preview de linhas (apenas primeiras)
        preview_linhas = []
        if primeiras_linhas:
            for numero_linha, row in primeiras_linhas[:max_linhas_preview]:
                preview_linhas.append({
                    "linha": numero_linha,
                    "dados_originais": row,
                })

        # Comentário: prepara resumo de validação
        resumo_validacao = {
            "total_colunas": len(resultado_mapeamento.matches),
            "colunas_mapeadas_alta": len(resultado_mapeamento.mapeamentos_altos),
            "colunas_mapeadas_media": len(resultado_mapeamento.mapeamentos_medios),
            "colunas_mapeadas_baixa": len(resultado_mapeamento.mapeamentos_baixos),
            "colunas_ignoradas": len(resultado_mapeamento.campos_ignorados),
            "campos_criticos_faltantes": list(resultado_mapeamento.campos_criticos_faltantes),
            "bloqueada": len(resultado_mapeamento.campos_criticos_faltantes) > 0,
            "requer_confirmacao": any(
                self._enriquecer_match_com_regra_bloqueio(m)["requer_confirmacao"]
                for m in resultado_mapeamento.matches
            ),
        }

        # Comentário: prepara avisos detalhados
        avisos = []
        if resultado_mapeamento.duplicatas:
            avisos.append(
                f"⚠️ Atenção: {len(resultado_mapeamento.duplicatas)} campo(s) "
                f"mapeado(s) por múltiplas colunas. "
                f"Será usada a coluna com maior confiança. "
                f"Campos: {', '.join(resultado_mapeamento.duplicatas.keys())}"
            )
        if resultado_mapeamento.campos_criticos_faltantes:
            avisos.append(
                f"🚫 BLOQUEIO: Campos críticos não encontrados: "
                f"{', '.join(resultado_mapeamento.campos_criticos_faltantes)}. "
                f"Importação será BLOQUEADA até que esses campos sejam mapeados com confiança ≥75%."
            )
        if resultado_mapeamento.mapeamentos_medios or resultado_mapeamento.mapeamentos_baixos:
            avisos.append(
                f"ℹ️ Confirmação necessária: "
                f"{len(resultado_mapeamento.mapeamentos_medios) + len(resultado_mapeamento.mapeamentos_baixos)} "
                f"mapeamento(s) com confiança média/baixa. "
                f"Revise antes de confirmar importação."
            )

        return {
            "colunas": colunas_preview,
            "preview_linhas": preview_linhas,
            "resumo_validacao": resumo_validacao,
            "avisos": avisos,
            "metadados": {
                "delimitador": resultado_mapeamento.metadados.delimitador if resultado_mapeamento.metadados else None,
                "numero_linha_cabecalho": resultado_mapeamento.metadados.numero_linha_cabecalho if resultado_mapeamento.metadados else 0,
                "score_deteccao_cabecalho": resultado_mapeamento.metadados.score_deteccao_cabecalho if resultado_mapeamento.metadados else 0.0,
                "hash_arquivo": resultado_mapeamento.metadados.hash_arquivo if resultado_mapeamento.metadados else None,
            },
        }

    def _detectar_delimitador(self, texto: str) -> str:
        """
        Detecta delimitador do arquivo (vírgula, ponto-e-vírgula, tab).

        Estratégia: usa csv.Sniffer (robusto) com fallback para heurística manual.
        """
        # Comentário: tenta Sniffer padrão do csv
        try:
            sample = "\n".join(texto.split("\n")[:5])
            delimitador = csv.Sniffer().sniff(sample).delimiter
            return delimitador
        except Exception:
            # Comentário: fallback para heurística simples
            pass

        # Comentário: conta ocorrências de delimitadores candidatos na primeira linha
        primeira_linha = texto.split("\n")[0] if texto else ""
        contadores = {
            ",": primeira_linha.count(","),
            ";": primeira_linha.count(";"),
            "\t": primeira_linha.count("\t"),
        }

        # Comentário: retorna delimitador mais frequente (padrão: vírgula)
        return max(contadores, key=contadores.get) or ","
