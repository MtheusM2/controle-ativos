"""Central de inferencia por e-mail para a revisao de importacao.

As regras ficam neste modulo para que preview, confirmacao e testes usem o
mesmo contrato. A inferencia nunca deve sobrescrever um valor valido vindo da
planilha ou uma edicao manual do usuario.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from utils.validators import SETORES_VALIDOS, UNIDADES_VALIDAS


LIMIAR_AUTO_APLICACAO = 0.9


@dataclass(frozen=True)
class SugestaoInferencia:
    """Sugestao calculada a partir do e-mail do responsavel."""

    campo: str
    valor: str
    confianca: float
    regra: str
    motivo: str
    requer_confirmacao: bool
    aplicada_automaticamente: bool


def _normalizar_token(valor: str | None) -> str:
    """Normaliza texto para comparacao resiliente a caixa e acentos."""
    valor_nfkd = unicodedata.normalize("NFKD", valor or "")
    sem_acentos = "".join(ch for ch in valor_nfkd if not unicodedata.combining(ch))
    return sem_acentos.strip().lower()


def _tokenizar_email(email: str | None) -> tuple[list[str], list[str], str]:
    """Separa local-part e dominio para permitir regras explicitas e parciais."""
    email_limpo = (email or "").strip().lower()
    if "@" not in email_limpo:
        return [], [], ""

    local_part, dominio = email_limpo.split("@", 1)
    padrao = r"[^a-z0-9]+"
    local_tokens = [token for token in re.split(padrao, _normalizar_token(local_part)) if token]
    dominio_tokens = [token for token in re.split(padrao, _normalizar_token(dominio)) if token]
    return local_tokens, dominio_tokens, _normalizar_token(dominio)


_SETOR_CANONICO_POR_TOKEN = {
    "ti": "T.I",
    "rh": "Rh",
    "adm": "Adm",
    "financeiro": "Financeiro",
    "vendas": "Vendas",
    "marketing": "Marketing",
    "infra": "Infraestrutura",
    "infraestrutura": "Infraestrutura",
    "apoio": "Apoio",
    "estagiarios": "Estagiários",
    "diretoria": "Diretoria",
    "manutencao": "Manutenção",
    "tecnica": "Técnica",
    "logistica": "Logística",
    "licitacao": "Licitação",
}

_SETOR_CANONICO_POR_NORMALIZADO = {
    _normalizar_token(valor): valor for valor in SETORES_VALIDOS
}

_LOCALIZACAO_CANONICA_POR_NORMALIZADO = {
    _normalizar_token(valor): valor for valor in UNIDADES_VALIDAS
}


def _valor_setor_valido(valor: str | None) -> bool:
    """Indica se o setor atual ja esta dentro do dominio oficial."""
    valor_norm = _normalizar_token(valor)
    return bool(valor_norm) and valor_norm in _SETOR_CANONICO_POR_NORMALIZADO


def _valor_localizacao_valido(valor: str | None) -> bool:
    """Indica se a localizacao atual ja esta dentro do dominio oficial."""
    valor_norm = _normalizar_token(valor)
    return bool(valor_norm) and valor_norm in _LOCALIZACAO_CANONICA_POR_NORMALIZADO


def _montar_candidato(_campo: str, valor: str, confianca: float, regra: str, motivo: str) -> tuple[str, float, str, str]:
    """Cria um candidato normalizado para as rotinas de inferencia."""
    return valor, confianca, regra, motivo


def _candidatos_setor(local_tokens: list[str], dominio_tokens: list[str]) -> list[tuple[str, float, str, str]]:
    """Gera candidatos de setor com prioridade por regras explicitas."""
    candidatos: list[tuple[str, float, str, str]] = []
    tokens = local_tokens + dominio_tokens

    for token in tokens:
        token_norm = _normalizar_token(token)
        if token_norm in _SETOR_CANONICO_POR_TOKEN:
            candidatos.append(
                _montar_candidato(
                    "setor",
                    _SETOR_CANONICO_POR_TOKEN[token_norm],
                    0.96,
                    "token_exato_local_part",
                    f"Token '{token}' do e-mail aponta diretamente para o setor.",
                )
            )

        # Regra de menor confianca para capturar abreviacoes ou tokens parciais.
        for chave, setor in _SETOR_CANONICO_POR_TOKEN.items():
            if token_norm == chave:
                continue
            if chave in token_norm or token_norm in chave:
                candidatos.append(
                    _montar_candidato(
                        "setor",
                        setor,
                        0.66,
                        "token_parcial",
                        f"Token parcial '{token}' sugere o setor '{setor}'.",
                    )
                )

    return candidatos


def _candidatos_localizacao(dominio_normalizado: str, dominio_tokens: list[str]) -> list[tuple[str, float, str, str]]:
    """Gera candidatos de localizacao/base com base no dominio do e-mail."""
    candidatos: list[tuple[str, float, str, str]] = []

    regras_exatas = {
        "opusmedical": "Opus Medical",
        "vicentemartins": "Vicente Martins",
    }

    for marcador, unidade in regras_exatas.items():
        if marcador in dominio_normalizado:
            candidatos.append(
                _montar_candidato(
                    "localizacao",
                    unidade,
                    0.94,
                    "dominio_exato",
                    f"Dominio contem o marcador '{marcador}' associado a '{unidade}'.",
                )
            )

    # Regra de fallback para dominos proximos, mas nao completamente conclusivos.
    for token in dominio_tokens:
        token_norm = _normalizar_token(token)
        if token_norm and "opus" in token_norm:
            candidatos.append(
                _montar_candidato(
                    "localizacao",
                    "Opus Medical",
                    0.68,
                    "dominio_parcial",
                    f"Token parcial '{token}' sugere a base 'Opus Medical'.",
                )
            )
        if token_norm and "vicente" in token_norm:
            candidatos.append(
                _montar_candidato(
                    "localizacao",
                    "Vicente Martins",
                    0.68,
                    "dominio_parcial",
                    f"Token parcial '{token}' sugere a base 'Vicente Martins'.",
                )
            )

    return candidatos


def _escolher_melhor_candidato(campo: str, candidatos: list[tuple[str, float, str, str]]) -> SugestaoInferencia | None:
    """Consolida os candidatos e sinaliza ambiguidade quando necessario."""
    if not candidatos:
        return None

    candidatos_ordenados = sorted(candidatos, key=lambda item: item[1], reverse=True)
    melhor_valor, melhor_confianca, melhor_regra, melhor_motivo = candidatos_ordenados[0]

    # Ambiguidade real: mais de um valor com a mesma confianca maxima.
    empatados = [item for item in candidatos_ordenados if abs(item[1] - melhor_confianca) < 1e-6]
    valores_empatados = {item[0] for item in empatados}
    ambiguidade = len(valores_empatados) > 1

    # Se a confianca for baixa ou houver empate, o usuario precisa confirmar.
    requer_confirmacao = ambiguidade or melhor_confianca < LIMIAR_AUTO_APLICACAO

    return SugestaoInferencia(
        campo=campo,
        valor=melhor_valor,
        confianca=melhor_confianca,
        regra=melhor_regra,
        motivo=melhor_motivo + (" Ambiguidade detectada." if ambiguidade else ""),
        requer_confirmacao=requer_confirmacao,
        aplicada_automaticamente=not requer_confirmacao,
    )


def inferir_campos_por_email(email: str | None) -> dict[str, SugestaoInferencia]:
    """Retorna sugestoes de inferencia sem alterar os dados de entrada."""
    local_tokens, dominio_tokens, dominio_normalizado = _tokenizar_email(email)
    if not local_tokens and not dominio_tokens:
        return {}

    sugestoes: dict[str, SugestaoInferencia] = {}

    sugestao_setor = _escolher_melhor_candidato("setor", _candidatos_setor(local_tokens, dominio_tokens))
    if sugestao_setor:
        sugestoes["setor"] = sugestao_setor

    sugestao_localizacao = _escolher_melhor_candidato(
        "localizacao",
        _candidatos_localizacao(dominio_normalizado, dominio_tokens),
    )
    if sugestao_localizacao:
        sugestoes["localizacao"] = sugestao_localizacao

    return sugestoes


def aplicar_inferencia_email_em_dados(
    dados: dict,
    *,
    campos_editados_manualmente: set[str] | None = None,
) -> tuple[dict, dict]:
    """Aplica a inferencia respeitando a prioridade das fontes de dados.

    Ordem de prioridade:
    1. valor explicito valido vindo da planilha
    2. valor corrigido manualmente no modal
    3. valor inferido automaticamente por e-mail
    4. sugestao pendente de confirmacao
    5. permanece ausente quando nao ha confianca suficiente
    """
    campos_editados_manualmente = campos_editados_manualmente or set()
    dados_saida = dict(dados or {})

    # Mantem a compatibilidade entre o campo oficial e o legado antes de inferir.
    if not dados_saida.get("setor") and dados_saida.get("departamento"):
        dados_saida["setor"] = dados_saida.get("departamento")
    if not dados_saida.get("departamento") and dados_saida.get("setor"):
        dados_saida["departamento"] = dados_saida.get("setor")

    sugestoes = inferir_campos_por_email(dados_saida.get("email_responsavel"))
    metadados = {
        "aplicadas": {},
        "sugestoes_pendentes": {},
        "origem_campos": {
            "setor": "original",
            "localizacao": "original",
        },
    }

    for campo, sugestao in sugestoes.items():
        valor_atual = (dados_saida.get(campo) or "").strip()

        # Valor manual sempre vence.
        if campo in campos_editados_manualmente:
            metadados["origem_campos"][campo] = "manual"
            continue

        # Valor valido da planilha tambem vence e nao e sobrescrito.
        if campo == "setor" and _valor_setor_valido(valor_atual):
            metadados["origem_campos"][campo] = "planilha_valida"
            continue
        if campo == "localizacao" and _valor_localizacao_valido(valor_atual):
            metadados["origem_campos"][campo] = "planilha_valida"
            continue

        if sugestao.requer_confirmacao:
            metadados["origem_campos"][campo] = "sugestao_pendente"
            metadados["sugestoes_pendentes"][campo] = {
                "valor": sugestao.valor,
                "confianca": sugestao.confianca,
                "regra": sugestao.regra,
                "motivo": sugestao.motivo,
                "requer_confirmacao": True,
                "aplicada_automaticamente": False,
            }
            continue

        # Inferencia automatica so ocorre quando a confianca e alta e nao ha conflito.
        dados_saida[campo] = sugestao.valor
        if campo == "setor":
            dados_saida["departamento"] = sugestao.valor

        metadados["origem_campos"][campo] = "inferido_automatico"
        metadados["aplicadas"][campo] = {
            "valor": sugestao.valor,
            "confianca": sugestao.confianca,
            "regra": sugestao.regra,
            "motivo": sugestao.motivo,
            "requer_confirmacao": False,
            "aplicada_automaticamente": True,
        }

    # Mantem a sincronia do alias legado apos as regras de prioridade.
    if "setor" in dados_saida and "departamento" not in dados_saida:
        dados_saida["departamento"] = dados_saida["setor"]
    if "departamento" in dados_saida and "setor" not in dados_saida:
        dados_saida["setor"] = dados_saida["departamento"]

    return dados_saida, metadados


# Alias de compatibilidade para consumidores legados que ainda importem o nome antigo.
aplicar_inferencia_email = aplicar_inferencia_email_em_dados