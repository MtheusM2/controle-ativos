# utils/import_mapper.py
#
# Motor de matching e scoring para mapeamento de colunas.
# Usa estratégia multi-camada com confiança numérica.
#
# Fluxo:
# 1. Nível 1: Correspondência Exata Normalizada (100%)
# 2. Nível 2: Sinônimo Oficial (95%)
# 3. Nível 3: Similaridade Textual (60–85%)
# 4. Nível 4: Sem Match (rejeita)
#

import unicodedata
import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional
from utils.import_schema import (
    obter_todos_campos,
    obter_campos_criticos,
    SINONIMOS_CAMPOS,
    PESO_CORRESPONDENCIA_EXATA,
    PESO_SINONIMO_OFICIAL,
    PESO_SIMILARIDADE_ALTA,
    PESO_SIMILARIDADE_MEDIA,
    PESO_SIMILARIDADE_BAIXA,
    PENALIDADE_COLISAO,
    LIMIAR_CONFIANCA_ALTA,
    LIMIAR_CONFIANCA_MEDIA,
    LIMIAR_CONFIANCA_BAIXA,
    LIMIAR_CONFIANCA_REJEITAR,
)


class ResultadoMatch:
    """
    Resultado de matching de uma coluna de origem para campo do domínio.
    """

    def __init__(
        self,
        coluna_origem: str,
        campo_destino: Optional[str] = None,
        score: float = 0.0,
        estrategia: str = "nao_mapeado",
        motivo: str = "",
    ):
        """
        Args:
            coluna_origem: Nome original da coluna no CSV
            campo_destino: Campo do domínio (ou None se não mapeado)
            score: Confiança numérica (0.0–1.0)
            estrategia: Como foi encontrado ("exata", "sinonimo", "similaridade", etc)
            motivo: Descrição textual do match
        """
        self.coluna_origem = coluna_origem
        self.campo_destino = campo_destino
        self.score = max(0.0, min(score, 1.0))  # Comentário: clipa para [0, 1]
        self.estrategia = estrategia
        self.motivo = motivo

    @property
    def confianca_alta(self) -> bool:
        """Indica se score está na faixa alta (≥90%)."""
        return self.score >= LIMIAR_CONFIANCA_ALTA / 100.0

    @property
    def confianca_media(self) -> bool:
        """Indica se score está na faixa média (75–89%)."""
        media = LIMIAR_CONFIANCA_MEDIA / 100.0
        alta = LIMIAR_CONFIANCA_ALTA / 100.0
        return media <= self.score < alta

    @property
    def confianca_baixa(self) -> bool:
        """Indica se score está na faixa baixa (60–74%)."""
        baixa = LIMIAR_CONFIANCA_BAIXA / 100.0
        media = LIMIAR_CONFIANCA_MEDIA / 100.0
        return baixa <= self.score < media

    @property
    def deve_ignorar(self) -> bool:
        """Indica se score está abaixo do limiar de rejeição (<60%)."""
        return self.score < LIMIAR_CONFIANCA_REJEITAR / 100.0

    def para_dict(self) -> Dict:
        """Serializa resultado para JSON."""
        return {
            "coluna_origem": self.coluna_origem,
            "campo_destino": self.campo_destino,
            "score": round(self.score, 2),
            "score_percentual": round(self.score * 100, 1),
            "estrategia": self.estrategia,
            "motivo": self.motivo,
            "confianca_alta": self.confianca_alta,
            "confianca_media": self.confianca_media,
            "confianca_baixa": self.confianca_baixa,
        }


class MotorMatching:
    """
    Motor de matching multi-estratégia para reconhecer colunas de CSV.
    """

    def __init__(self):
        """Inicializa motor com dicionários do schema."""
        # Comentário: obtém constantes do schema
        self.campos_validos = obter_todos_campos()
        self.campos_criticos = obter_campos_criticos()
        self.sinonimos = SINONIMOS_CAMPOS

    def processar_cabecalho(self, headers: List[str]) -> List[ResultadoMatch]:
        """
        Processa lista de cabeçalhos e retorna matches com scores.

        Args:
            headers: Lista de nomes de coluna (já normalizados para lowercase)

        Returns:
            Lista de ResultadoMatch, ordenada por score descendente
        """
        # Comentário: processa cada coluna
        matches = []
        for coluna_original in headers:
            match = self.fazer_match(coluna_original)
            matches.append(match)

        # Comentário: detecta e penaliza colisões (duas colunas mapeam para mesmo campo)
        matches = self._processar_colisoes(matches)

        # Comentário: ordena por score para facilitar análise
        matches.sort(key=lambda m: m.score, reverse=True)

        return matches

    def fazer_match(self, coluna: str) -> ResultadoMatch:
        """
        Faz matching de uma coluna contra o schema.

        Estratégia em cascata:
        1. Exata normalizada
        2. Sinônimo oficial
        3. Similaridade
        4. Rejeita

        Args:
            coluna: Nome de coluna (esperado em lowercase)

        Returns:
            ResultadoMatch com melhor match encontrado
        """
        # Comentário: normaliza entrada (garantir segurança)
        coluna_norm = self._normalizar_coluna(coluna)

        if not coluna_norm:
            # Comentário: coluna vazia após normalização
            return ResultadoMatch(
                coluna_origem=coluna,
                campo_destino=None,
                score=0.0,
                estrategia="nao_mapeado",
                motivo="Coluna vazia após normalização.",
            )

        # ===== NÍVEL 1: Correspondência Exata =====
        # Comentário: procura match exato com campo official normalizado
        match_exato = self._tentar_match_exato(coluna_norm)
        if match_exato:
            return match_exato

        # ===== NÍVEL 2: Sinônimo Oficial =====
        # Comentário: procura em dicionário de sinônimos
        match_sinonimo = self._tentar_match_sinonimo(coluna_norm)
        if match_sinonimo:
            return match_sinonimo

        # ===== NÍVEL 3: Similaridade Textual =====
        # Comentário: busca campos similares usando difflib
        match_similaridade = self._tentar_match_similaridade(coluna_norm)
        if match_similaridade and not match_similaridade.deve_ignorar:
            return match_similaridade

        # ===== NÍVEL 4: Rejeita =====
        # Comentário: nenhum match encontrado acima do limiar
        return ResultadoMatch(
            coluna_origem=coluna,
            campo_destino=None,
            score=0.0,
            estrategia="nao_mapeado",
            motivo="Sem correspondência válida no schema do sistema.",
        )

    def _normalizar_coluna(self, coluna: str) -> str:
        """
        Normaliza nome de coluna para comparação consistente.

        Passos:
        1. Remove acentos via NFD (decomposição Unicode)
        2. Converte para lowercase
        3. Trata hífens, underscores e espaços como equivalentes
        4. Remove caracteres especiais
        5. Reduz espaços múltiplos a um só

        Comentário: Estratégia segura: espaço/hífen/underscore são tratados como separadores
        equivalentes, permitindo matching flexível sem falsos positivos.
        """
        # Comentário: garante string
        valor = str(coluna or "").strip()

        # Comentário: remove acentos via NFD (decomposição)
        sem_acentos = "".join(
            c
            for c in unicodedata.normalize("NFD", valor)
            if unicodedata.category(c) != "Mn"  # Remove marcas diacríticas
        )

        # Comentário: normaliza caso
        minuscula = sem_acentos.lower()

        # Comentário: NOVO: trata hífens e underscores como espaços (separadores equivalentes)
        # Exemplo: "data-entrada" → "data entrada", "tipo_ativo" → "tipo ativo"
        com_separadores_unificados = minuscula.replace("-", " ").replace("_", " ")

        # Comentário: remove caracteres especiais, mantém alfanuméricos e espaço
        sem_especiais = re.sub(r"[^a-z0-9 ]", "", com_separadores_unificados)

        # Comentário: reduz espaços múltiplos a um só
        normalizado = re.sub(r"\s+", " ", sem_especiais).strip()

        return normalizado

    def _tentar_match_exato(self, coluna_norm: str) -> Optional[ResultadoMatch]:
        """
        Tenta correspondência exata com campo official (após normalização).

        Comentário: os nomes de campo no schema estão em underscore (tipo_ativo)
        mas a coluna normalizada pode estar com espaço ("tipo ativo").
        Fazemos match tratando espaço e underscore como equivalentes.
        """
        # Comentário: substitui espaço por underscore para comparação
        coluna_com_underscore = coluna_norm.replace(" ", "_")

        # Comentário: tenta match exato direto
        if coluna_com_underscore in self.campos_validos:
            return ResultadoMatch(
                coluna_origem=coluna_norm,
                campo_destino=coluna_com_underscore,
                score=PESO_CORRESPONDENCIA_EXATA / 100.0,
                estrategia="exata",
                motivo="Correspondência exata com schema.",
            )

        # Comentário: tenta variações comuns (espaço vs underscore)
        coluna_com_espaco = coluna_norm.replace("_", " ")
        for campo_oficial in self.campos_validos:
            if campo_oficial.replace("_", " ") == coluna_com_espaco:
                return ResultadoMatch(
                    coluna_origem=coluna_norm,
                    campo_destino=campo_oficial,
                    score=PESO_CORRESPONDENCIA_EXATA / 100.0,
                    estrategia="exata",
                    motivo="Correspondência exata (separadores tratados como equivalentes).",
                )

        return None

    def _tentar_match_sinonimo(self, coluna_norm: str) -> Optional[ResultadoMatch]:
        """
        Tenta match em dicionário de sinônimos.

        Comentário: sinônimos são strings explícitas definidas no schema
        """
        # Comentário: procura direto no dicionário
        campo_mapeado = self.sinonimos.get(coluna_norm)

        if campo_mapeado:
            return ResultadoMatch(
                coluna_origem=coluna_norm,
                campo_destino=campo_mapeado,
                score=PESO_SINONIMO_OFICIAL / 100.0,
                estrategia="sinonimo",
                motivo=f"Sinônimo reconhecido: '{coluna_norm}' → '{campo_mapeado}'.",
            )

        # Comentário: tenta variação com espaço/underscore
        coluna_com_underscore = coluna_norm.replace(" ", "_")
        campo_mapeado_alt = self.sinonimos.get(coluna_com_underscore)
        if campo_mapeado_alt:
            return ResultadoMatch(
                coluna_origem=coluna_norm,
                campo_destino=campo_mapeado_alt,
                score=PESO_SINONIMO_OFICIAL / 100.0,
                estrategia="sinonimo",
                motivo=f"Sinônimo reconhecido (variação): '{coluna_com_underscore}' → '{campo_mapeado_alt}'.",
            )

        return None

    def _tentar_match_similaridade(self, coluna_norm: str) -> Optional[ResultadoMatch]:
        """
        Tenta match por similaridade textual (difflib.SequenceMatcher).

        Estratégia:
        1. Calcula similaridade contra cada campo válido
        2. Retorna melhor match acima de limiar (0.65)
        3. Score é mapeado para faixas de confiança
        4. Penaliza ambigüidades (múltiplos matches com scores próximos)

        Comentário: A similaridade é proporcional à confiança, mas cuidado com falsos positivos.
        """
        # Comentário: compara contra todos os campos oficiais
        matches_similares = []

        for campo in self.campos_validos:
            # Comentário: calcula similaridade ratio (0.0–1.0)
            # Trata espaço e underscore como equivalentes no score
            campo_normalizado = campo.replace("_", " ")
            similaridade = SequenceMatcher(None, coluna_norm, campo_normalizado).ratio()

            # Comentário: mantém matches acima de limiar mínimo
            if similaridade >= 0.65:
                matches_similares.append((campo, similaridade))

        # Comentário: se nenhum match, retorna None
        if not matches_similares:
            return None

        # Comentário: ordena por similaridade decrescente
        matches_similares.sort(key=lambda x: x[1], reverse=True)
        melhor_match, melhor_similaridade = matches_similares[0]

        # Comentário: detec ambigüidade: múltiplos matches com scores muito próximos
        tem_ambiguidade = False
        if len(matches_similares) > 1:
            segundo_score = matches_similares[1][1]
            # Comentário: se diferença < 0.10 (10%), considera ambíguo
            if abs(melhor_similaridade - segundo_score) < 0.10:
                tem_ambiguidade = True

        # Comentário: mapeia similaridade para score ponderado
        if melhor_similaridade >= 0.90:
            score = PESO_SIMILARIDADE_ALTA / 100.0  # 0.85
        elif melhor_similaridade >= 0.80:
            score = PESO_SIMILARIDADE_ALTA / 100.0  # 0.85
        elif melhor_similaridade >= 0.75:
            score = PESO_SIMILARIDADE_MEDIA / 100.0  # 0.75
        elif melhor_similaridade >= 0.70:
            score = PESO_SIMILARIDADE_MEDIA / 100.0  # 0.75
        else:
            score = PESO_SIMILARIDADE_BAIXA / 100.0  # 0.60

        # Comentário: penaliza ambigüidade reduzindo score
        if tem_ambiguidade:
            score = max(0.0, score - 0.15)
            motivo_extra = " [⚠️ Ambíguo: múltiplos matches similares]"
        else:
            motivo_extra = ""

        return ResultadoMatch(
            coluna_origem=coluna_norm,
            campo_destino=melhor_match,
            score=score,
            estrategia="similaridade",
            motivo=f"Similaridade textual: '{coluna_norm}' ~= '{melhor_match}' ({melhor_similaridade:.0%}).{motivo_extra}",
        )

    def _processar_colisoes(self, matches: List[ResultadoMatch]) -> List[ResultadoMatch]:
        """
        Detecta e penaliza colisões (múltiplas colunas mapeam para mesmo campo).

        Comentário: se duas colunas mapeam para o mesmo campo:
        - Mantém a com maior score
        - Reduz score das demais (penalidade)
        """
        # Comentário: agrupa matches por campo_destino
        mapeamentos_por_campo: Dict[str, List[ResultadoMatch]] = {}
        for match in matches:
            if match.campo_destino:
                if match.campo_destino not in mapeamentos_por_campo:
                    mapeamentos_por_campo[match.campo_destino] = []
                mapeamentos_por_campo[match.campo_destino].append(match)

        # Comentário: detecta e penaliza colisões
        for campo, lista_matches in mapeamentos_por_campo.items():
            if len(lista_matches) > 1:
                # Comentário: ordena por score, mantém melhor, penaliza demais
                lista_matches.sort(key=lambda m: m.score, reverse=True)
                for idx, match in enumerate(lista_matches[1:], 1):
                    # Comentário: reduz score de duplicatas
                    match.score = max(0.0, match.score - PENALIDADE_COLISAO / 100.0)
                    match.motivo += f" [Colisão: campo '{campo}' já mapeado com score maior]"

        return matches

    def validar_ambiguidade_colisao(
        self,
        matches: List[ResultadoMatch],
    ) -> Dict[str, List[ResultadoMatch]]:
        """
        Identifica colisões: múltiplas colunas mapeam para o mesmo campo.

        Returns:
            Dict {campo_destino → [lista de matches em colisão]}
            Se campo tem apenas 1 match, não aparece no dict.
        """
        colisoes = {}
        mapeamentos_por_campo: Dict[str, List[ResultadoMatch]] = {}

        for match in matches:
            if match.campo_destino:
                if match.campo_destino not in mapeamentos_por_campo:
                    mapeamentos_por_campo[match.campo_destino] = []
                mapeamentos_por_campo[match.campo_destino].append(match)

        # Comentário: apenas campos com >1 match (colisão)
        for campo, lista_matches in mapeamentos_por_campo.items():
            if len(lista_matches) > 1:
                colisoes[campo] = lista_matches

        return colisoes
