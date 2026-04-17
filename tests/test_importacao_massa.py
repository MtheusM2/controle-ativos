from __future__ import annotations

import pytest

from services.ativos_service import AtivoErro, AtivosService


def _service_admin() -> AtivosService:
    """
    Cria service com contexto administrativo para liberar importação em testes.
    """
    service = AtivosService()
    service._obter_contexto_acesso = lambda _user_id: {  # type: ignore[attr-defined]
        "perfil": "adm",
        "empresa_id": 1,
    }
    return service


def test_preview_importacao_classifica_exatas_sugeridas_e_ignoradas():
    """
    Preview deve separar corretamente colunas exatas, sugeridas e bloqueadas.
    """
    service = _service_admin()
    conteudo_csv = (
        "tipo_ativo,marca,modelo,setor,status,data_entrada,teamviewer id,anydesk id,PC,IMEI,password\n"
        "Notebook,Dell,XPS,T.I,Dispon\u00edvel,2026-04-17,123456789,ABC-DEF-123,maquina-01,999999999999999,minha_senha\n"
    ).encode("utf-8")

    resultado = service.gerar_preview_importacao_csv(conteudo_csv, user_id=1)

    exatas = resultado["colunas"]["exatas"]
    sugeridas = resultado["colunas"]["sugeridas"]
    ignoradas = resultado["colunas"]["ignoradas"]
    resumo = resultado["resumo_validacao"]

    assert any(item["campo_destino"] == "tipo_ativo" for item in exatas)
    assert any(item["campo_sugerido"] == "teamviewer_id" for item in sugeridas)
    assert any(item["campo_sugerido"] == "anydesk_id" for item in sugeridas)
    assert any(item["coluna_origem"] == "PC" for item in ignoradas)
    assert any(item["coluna_origem"] == "IMEI" for item in ignoradas)
    assert any(item["coluna_origem"] == "password" for item in ignoradas)
    assert resumo["total_linhas"] == 1
    assert resumo["linhas_validas"] == 1


def test_confirmar_importacao_aplica_sugestoes_confirmadas_teamviewer_anydesk():
    """
    Confirmação deve importar TeamViewer/AnyDesk somente quando usuário aprova sugestão.
    """
    service = _service_admin()
    ativos_capturados = []

    def _criar_ativo_fake(ativo, _user_id):
        ativos_capturados.append(ativo)
        return f"OPU-{len(ativos_capturados):06d}"

    service.criar_ativo = _criar_ativo_fake  # type: ignore[method-assign]

    conteudo_csv = (
        "tipo_ativo,marca,modelo,setor,status,data_entrada,teamviewer id,anydesk id\n"
        "Notebook,Dell,XPS,T.I,Dispon\u00edvel,2026-04-17,123456789,ABC-DEF-123\n"
    ).encode("utf-8")

    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={
            "teamviewer id": "teamviewer_id",
            "anydesk id": "anydesk_id",
        },
        user_id=1,
        modo_tudo_ou_nada=True,
    )

    assert resultado["ok_importacao"] is True
    assert resultado["importados"] == 1
    assert len(ativos_capturados) == 1
    assert ativos_capturados[0].teamviewer_id == "123456789"
    assert ativos_capturados[0].anydesk_id == "ABC-DEF-123"
    assert ativos_capturados[0].imei_1 is None
    assert ativos_capturados[0].imei_2 is None


def test_confirmar_importacao_sem_confirmar_sugestao_mantem_schema_first():
    """
    Sem confirmação de sugestão, campo sugerido não entra e linha pode falhar por ausência.
    """
    service = _service_admin()
    conteudo_csv = (
        "tipo ativo,marca,modelo,setor,status,data_entrada\n"
        "Notebook,Dell,XPS,T.I,Dispon\u00edvel,2026-04-17\n"
    ).encode("utf-8")

    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={},
        user_id=1,
        modo_tudo_ou_nada=True,
    )

    assert resultado["ok_importacao"] is False
    assert resultado["importados"] == 0
    assert resultado["falhas"] >= 1
    assert any("tipo" in erro.lower() for erro in resultado["erros"])


def test_confirmar_importacao_tudo_ou_nada_bloqueia_persistencia_com_linha_invalida():
    """
    Em modo tudo-ou-nada, qualquer erro de linha impede gravação parcial silenciosa.
    """
    service = _service_admin()
    criacoes = {"total": 0}

    def _criar_ativo_fake(_ativo, _user_id):
        criacoes["total"] += 1
        return f"OPU-{criacoes['total']:06d}"

    service.criar_ativo = _criar_ativo_fake  # type: ignore[method-assign]

    conteudo_csv = (
        "tipo_ativo,marca,modelo,setor,status,data_entrada\n"
        "Notebook,Dell,XPS,T.I,Dispon\u00edvel,2026-04-17\n"
        "Notebook,Dell,XPS,T.I,Status Invalido,2026-04-17\n"
    ).encode("utf-8")

    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={},
        user_id=1,
        modo_tudo_ou_nada=True,
    )

    assert resultado["ok_importacao"] is False
    assert resultado["importados"] == 0
    assert resultado["falhas"] >= 1
    assert criacoes["total"] == 0


def test_confirmar_importacao_rejeita_coluna_imei_sem_reintroduzir_no_dominio():
    """
    Coluna IMEI deve ser descartada no contrato e não pode reaparecer no objeto persistido.
    """
    service = _service_admin()
    ativos_capturados = []

    def _criar_ativo_fake(ativo, _user_id):
        ativos_capturados.append(ativo)
        return "OPU-000001"

    service.criar_ativo = _criar_ativo_fake  # type: ignore[method-assign]

    conteudo_csv = (
        "tipo_ativo,marca,modelo,setor,status,data_entrada,imei_1\n"
        "Notebook,Dell,XPS,T.I,Dispon\u00edvel,2026-04-17,999999999999999\n"
    ).encode("utf-8")

    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={},
        user_id=1,
        modo_tudo_ou_nada=True,
    )

    assert resultado["ok_importacao"] is True
    assert ativos_capturados[0].imei_1 is None
    assert ativos_capturados[0].imei_2 is None


def test_preview_importacao_rejeita_csv_vazio():
    """
    CSV vazio deve falhar cedo com erro objetivo para o usuário.
    """
    service = _service_admin()

    with pytest.raises(AtivoErro):
        service.gerar_preview_importacao_csv(b"", user_id=1)
