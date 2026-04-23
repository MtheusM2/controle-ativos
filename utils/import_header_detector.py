# utils/import_header_detector.py
#
# Detector robusto de linha de cabeçalho em CSV/planilhas.
# Detecta automaticamente onde estão os nomes das colunas, mesmo que haja
# linhas de lixo acima (título, descrição, etc).
#
# Estratégia:
# 1. Escaneia primeiras N linhas
# 2. Calcula score para cada linha candidata
# 3. Escolhe linha com maior score acima do limiar
#

import re
from typing import List, Tuple
from utils.import_schema import obter_todos_campos, SINONIMOS_CAMPOS


class DetectorCabecalho:
    """
    Detecta linha de cabeçalho em CSV/planilha.
    Suporta cabeçalhos em qualquer posição nas primeiras linhas.
    """

    # Limite de linhas a escanear no início do arquivo
    LINHAS_MAX_SCAN = 30

    # Limiar mínimo de score para aceitar linha candidata como cabeçalho
    LIMIAR_SCORE_CABECALHO = 0.50

    # Padrões para detectar linhas de "lixo" (não é cabeçalho)
    REGEX_LINHA_LIXO = re.compile(
        r"^(título|titulo|sheet|planilha|dados|tabela|importar|ativos|#|--|===|\*\*)",
        re.IGNORECASE
    )

    def __init__(self):
        """Inicializa detector com campos válidos do schema."""
        # Comentário: obtém lista de campos oficiais para matching
        self.campos_validos = obter_todos_campos()
        self.sinonimos = SINONIMOS_CAMPOS

    def detectar_cabecalho(
        self,
        linhas: List[str],
        delimitador: str = ","
    ) -> Tuple[int, List[str], float]:
        """
        Detecta linha de cabeçalho em lista de strings.

        Args:
            linhas: Lista de linhas do arquivo (str, já decodificadas)
            delimitador: Separador de colunas (padrão: vírgula)

        Returns:
            Tupla (numero_linha, headers, score_confianca)
            - numero_linha: 0-indexed (0 = primeira linha)
            - headers: Lista de nomes de coluna
            - score_confianca: 0.0–1.0

        Raises:
            ValueError: Se nenhuma linha válida encontrada
        """
        # Comentário: processa apenas primeiras N linhas
        linhas_a_escanear = linhas[: self.LINHAS_MAX_SCAN]

        scores_candidatas = []
        for idx, linha in enumerate(linhas_a_escanear):
            # Comentário: pula linhas claramente vazias
            if not linha or not linha.strip():
                continue

            # Comentário: divide por delimitador
            campos = self._dividir_linha(linha, delimitador)
            if not campos or len(campos) < 2:
                # Comentário: cabeçalho deve ter pelo menos 2 colunas
                continue

            # Comentário: calcula score para linha candidata
            score = self._calcular_score_candidata(campos)
            scores_candidatas.append((idx, campos, score))

        # Comentário: se nenhuma candidata aprovada
        if not scores_candidatas:
            raise ValueError(
                "Nenhuma linha de cabeçalho válida detectada nos primeiros "
                f"{self.LINHAS_MAX_SCAN} registros."
            )

        # Comentário: ordena por score e retorna melhor candidata acima do limiar
        scores_candidatas.sort(key=lambda x: x[2], reverse=True)
        melhor_idx, melhor_headers, melhor_score = scores_candidatas[0]

        # Comentário: valida limiar mínimo de confiança
        if melhor_score < self.LIMIAR_SCORE_CABECALHO:
            raise ValueError(
                f"Melhor candidata de cabeçalho tem score baixo ({melhor_score:.2%}). "
                "Arquivo pode estar malformado ou com estrutura inesperada."
            )

        # Comentário: normaliza headers para lowercase (processamento posterior espera isso)
        headers_normalizados = [h.lower().strip() for h in melhor_headers]

        return melhor_idx, headers_normalizados, melhor_score

    def _dividir_linha(self, linha: str, delimitador: str) -> List[str]:
        """
        Divide linha por delimitador, tratando aspas.

        Comentário: implementação simples; para CSV robusto, use csv.DictReader
        """
        # Comentário: se a linha contém aspas, pode ser CSV com campos escapados
        if '"' in linha:
            # Comentário: abordagem simplificada: split direto
            # Nota: importador principal usa csv.DictReader, que é mais robusto
            return [campo.strip().strip('"') for campo in linha.split(delimitador)]
        else:
            return [campo.strip() for campo in linha.split(delimitador)]

    def _calcular_score_candidata(self, campos: List[str]) -> float:
        """
        Calcula score de probabilidade de que 'campos' é uma linha de cabeçalho.

        Componentes:
        1. Densidade de tokens não-vazios
        2. Quantidade de campos reconhecíveis (sinônimos + oficiais)
        3. Penalidade se parece com linha de lixo
        4. Penalidade se contém muitos números puros (sinal de dados, não cabeçalho)

        Retorna valor entre 0.0 e 1.0.
        """
        # Comentário: normaliza para lowercase para buscas
        campos_norm = [c.lower().strip() for c in campos if c.strip()]

        if not campos_norm:
            return 0.0

        score = 0.0

        # ====== Componente 1: Densidade de não-vazios ======
        # Comentário: cabeçalho deve ter maioria de colunas com nome
        densidade_nao_vazio = len(campos_norm) / len(campos) if campos else 0.0
        score += densidade_nao_vazio * 20  # peso: até 20 pontos

        # ====== Componente 2: Reconhecimento de campos ======
        # Comentário: quantos campos são reconhecidos (sinônimo ou oficial)?
        campos_reconhecidos = 0
        for campo in campos_norm:
            # Comentário: tenta match exato com campo oficial
            if campo in self.campos_validos:
                campos_reconhecidos += 1
            # Comentário: tenta match com sinônimo
            elif self.sinonimos.get(campo):
                campos_reconhecidos += 1
            # Comentário: tenta match parcial (primeiras 3+ letras)
            elif any(campo.startswith(f[:3]) for f in self.campos_validos if len(f) >= 3):
                campos_reconhecidos += 0.5

        proporcao_reconhecidos = campos_reconhecidos / len(campos_norm) if campos_norm else 0.0
        score += proporcao_reconhecidos * 60  # peso: até 60 pontos

        # ====== Componente 3: Penalidade por lixo ======
        # Comentário: rejeita se parece com título/descrição
        primeira_coluna = campos_norm[0] if campos_norm else ""
        if self.REGEX_LINHA_LIXO.search(primeira_coluna):
            score *= 0.3  # Comentário: reduz drasticamente se detecta padrão de lixo

        # ====== Componente 4: Penalidade por valores puros ======
        # Comentário: cabeçalhos não devem ter muitos números puros (indicativo de dados)
        campos_numericos = sum(
            1 for campo in campos_norm
            if campo.replace(".", "").replace(",", "").replace("-", "").isdigit()
        )
        proporcao_numerica = campos_numericos / len(campos_norm) if campos_norm else 0.0
        if proporcao_numerica > 0.5:
            # Comentário: se >50% das colunas são números puros, provavelmente é linha de dados
            score *= 0.2

        # ====== Normalização final para 0.0–1.0 ======
        # Comentário: score bruto está em 0–100, divide por 100
        return min(score / 100.0, 1.0)

    def validar_cabecalho_manual(self, linha: str, delimitador: str = ",") -> List[str]:
        """
        Processa linha especificada manualmente como cabeçalho.
        Útil para UI ofercer seleção manual quando auto-detecção falha.

        Args:
            linha: String de linha de cabeçalho
            delimitador: Separador de colunas

        Returns:
            Lista de headers normalizados

        Raises:
            ValueError: Se linha não é válida (vazia, muito poucas colunas)
        """
        # Comentário: usa mesmo parsing que auto-detecção
        campos = self._dividir_linha(linha, delimitador)
        if not campos or len(campos) < 2:
            raise ValueError("Cabeçalho deve conter pelo menos 2 colunas.")

        # Comentário: normaliza e retorna
        return [h.lower().strip() for h in campos]
