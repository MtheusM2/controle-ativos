from __future__ import annotations

from services.importacao_service_seguranca import ServicoImportacaoComSeguranca


CSV_PREVIEW_SEGURO = (
    "tipo_ativo,marca,modelo,setor,status,data_entrada,usuario_responsavel,email_responsavel\n"
    "notebook,Dell,Latitude,rh,disponivel,2026-01-15,Ana Silva,ana@example.com\n"
).encode("utf-8")


def _stub_auditoria(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.importacao_service_seguranca.AuditoriaImportacaoService.iniciar_auditoria",
        lambda **kwargs: "IMP-TEST-RUNTIME",
    )
    monkeypatch.setattr(
        "services.importacao_service_seguranca.AuditoriaImportacaoService.obter_usuarios_validos",
        lambda empresa_id: {"Ana Silva"},
    )
    monkeypatch.setattr(
        "services.importacao_service_seguranca.AuditoriaImportacaoService.detectar_duplicatas",
        lambda ids_csv, empresa_id: {},
    )
    monkeypatch.setattr(
        "services.importacao_service_seguranca.AuditoriaImportacaoService.detectar_seriais_duplicados",
        lambda seriais_csv, empresa_id: {},
    )
    monkeypatch.setattr(
        "services.importacao_service_seguranca.AuditoriaImportacaoService.registrar_preview_gerado",
        lambda **kwargs: None,
    )


def test_preview_seguro_chama_normalizador_no_runtime_real(monkeypatch):
    _stub_auditoria(monkeypatch)

    chamadas = []
    import services.importacao_service_seguranca as modulo_preview

    normalizador_original = modulo_preview.normalizar_dados_importacao_valores

    def _normalizador_spy(dados):
        chamadas.append(dict(dados))
        return normalizador_original(dados)

    monkeypatch.setattr(
        modulo_preview,
        "normalizar_dados_importacao_valores",
        _normalizador_spy,
    )

    service = ServicoImportacaoComSeguranca()
    _id_lote, preview = service.gerar_preview_seguro(
        conteudo_csv=CSV_PREVIEW_SEGURO,
        usuario_id=1,
        empresa_id=10,
        endereco_ip="127.0.0.1",
        user_agent="pytest-runtime",
    )

    assert chamadas, "normalizar_dados_importacao_valores deveria ter sido chamado pelo preview seguro"
    assert preview["validacao_detalhes"]["linhas_validas"] > 0
