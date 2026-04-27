from __future__ import annotations

from utils.email_inference import aplicar_inferencia_email_em_dados, inferir_campos_por_email


def test_inferir_campos_por_email_ti_opusmedical_alta_confianca():
    """Email corporativo de TI na Opus deve gerar sugestoes fortes para setor/localizacao."""
    sugestoes = inferir_campos_por_email("ti@opusmedical.com.br")

    assert sugestoes["setor"].valor == "T.I"
    assert sugestoes["setor"].requer_confirmacao is False
    assert sugestoes["localizacao"].valor == "Opus Medical"
    assert sugestoes["localizacao"].requer_confirmacao is False


def test_aplicar_inferencia_nao_sobrescreve_valor_valido_existente():
    """Prioridade: valor valido da planilha permanece acima da inferencia."""
    dados_iniciais = {
        "email_responsavel": "ti@opusmedical.com.br",
        "setor": "Rh",
        "departamento": "Rh",
        "localizacao": "Vicente Martins",
    }

    dados_saida, metadados = aplicar_inferencia_email_em_dados(dados_iniciais)

    assert dados_saida["setor"] == "Rh"
    assert dados_saida["localizacao"] == "Vicente Martins"
    assert metadados["origem_campos"]["setor"] == "planilha_valida"
    assert metadados["origem_campos"]["localizacao"] == "planilha_valida"


def test_aplicar_inferencia_preenche_quando_ausente():
    """Sem setor/localizacao validos, inferencia de alta confianca deve preencher automaticamente."""
    dados_iniciais = {
        "email_responsavel": "ti@opusmedical.com.br",
        "setor": "",
        "localizacao": "",
    }

    dados_saida, metadados = aplicar_inferencia_email_em_dados(dados_iniciais)

    assert dados_saida["setor"] == "T.I"
    # Contrato canonico da Fase 1: retorno interno usa apenas "setor", sem alias legado "departamento".
    assert "departamento" not in dados_saida
    assert dados_saida["localizacao"] == "Opus Medical"
    assert "setor" in metadados["aplicadas"]
    assert "localizacao" in metadados["aplicadas"]


def test_aplicar_inferencia_respeita_edicao_manual():
    """Valor editado manualmente nunca deve ser sobrescrito por inferencia automatica."""
    dados_iniciais = {
        "email_responsavel": "rh@vicentemartins.com.br",
        "setor": "",
        "localizacao": "",
    }

    dados_saida, metadados = aplicar_inferencia_email_em_dados(
        dados_iniciais,
        campos_editados_manualmente={"setor"},
    )

    assert dados_saida.get("setor", "") == ""
    assert dados_saida["localizacao"] == "Vicente Martins"
    assert metadados["origem_campos"]["setor"] == "manual"


def test_aplicar_inferencia_marca_sugestao_pendente_quando_confianca_baixa():
    """Inferencias fracas nao devem sobrescrever o valor e precisam de confirmacao."""
    dados_iniciais = {
        "email_responsavel": "ti2@empresa.com.br",
        "setor": "",
        "localizacao": "",
    }

    dados_saida, metadados = aplicar_inferencia_email_em_dados(dados_iniciais)

    assert dados_saida.get("setor", "") == ""
    assert "setor" in metadados["sugestoes_pendentes"]
    assert metadados["sugestoes_pendentes"]["setor"]["requer_confirmacao"] is True


def test_inferir_campos_por_email_sugere_localizacao_por_dominio_parcial():
    """Dominios proximos da base devem virar sugestao, nao auto-aplicacao silenciosa."""
    sugestoes = inferir_campos_por_email("suporte@opusmed.com.br")

    assert "localizacao" in sugestoes
    assert sugestoes["localizacao"].valor == "Opus Medical"
    assert sugestoes["localizacao"].requer_confirmacao is True
