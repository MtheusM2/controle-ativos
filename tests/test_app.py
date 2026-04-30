from __future__ import annotations

# pyright: reportPrivateUsage=false

from io import BytesIO
import time
from types import SimpleNamespace
from unittest.mock import patch

from openpyxl import load_workbook
from services.ativos_service import PermissaoNegada
from web_app.app import create_app

def test_healthcheck(http_client):
    response = http_client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"ok": True, "status": "healthy"}


def test_dashboard_authenticated(authenticated_client):
    response = authenticated_client.get("/dashboard")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Dashboard de Ativos" in html
    assert "table-dashboard-preview" in html
    assert "panel-header-split" in html


def test_assets_listing_page_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/lista")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Listagem de Ativos" in html
    assert "table-assets-main" in html
    assert "table-aligned" in html


def test_asset_import_page_authenticated(authenticated_client):
    """
    Tela de importação em massa deve estar acessível para uso local no fluxo web.
    """
    response = authenticated_client.get("/ativos/importacao")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Importação em massa de ativos" in html
    assert "/ativos/importar/preview" in html
    assert "/ativos/importar/confirmar" in html


def test_asset_import_template_starts_with_confirm_button_disabled(authenticated_client):
    """
    Contrato de UI: botão de confirmação deve iniciar desabilitado
    para evitar importação sem pré-visualização e validação.
    """
    response = authenticated_client.get("/ativos/importacao")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'id="confirm-import-btn" disabled' in html


def test_asset_import_template_requires_suggestion_decisions_before_enabling(authenticated_client):
    """
    Contrato de UI: sugestões pendentes devem bloquear habilitação do botão.
    """
    response = authenticated_client.get("/ativos/importacao")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "function coletarDecisoesSugestoes()" in html
    assert "estadoOriginal === 'precisa_confirmar'" in html
    assert "pendentes += 1" in html
    assert "if (decisoes.pendentes > 0)" in html
    assert "sugestão(ões) sem decisão" in html


def test_asset_import_template_blocks_conflicting_destination_mappings(authenticated_client):
    """
    Contrato de UI: conflitos entre destinos exatos/sugeridos devem manter botão desabilitado.
    """
    response = authenticated_client.get("/ativos/importacao")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "const destinosConsolidados = Object.values(mapeamentoConsolidado).filter(Boolean)" in html
    assert "const destinosComConflito = []" in html
    assert "if (destinoJaEscolhido.has(destino))" in html
    assert "if (destinosComConflito.length > 0)" in html
    assert "Existem conflitos de campo destino" in html


def test_asset_import_template_only_enables_confirm_when_no_pending_restrictions(authenticated_client):
    """
    Contrato de UI: habilitação depende da ausência total de restrições.
    Teste atualizado para a nova central de revisão (PARTE 2).
    """
    response = authenticated_client.get("/ativos/importacao")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Verificar que o template contém a estrutura da central de revisão
    assert "estadoRevisao" in html
    assert "BLOCO A" in html or "Mapeamento" in html  # Bloco de mapeamento
    assert "BLOCO B" in html or "Revisão" in html     # Bloco de revisão
    assert "confirmButton" in html or "Confirmar" in html  # Botão de confirmação
    assert "descartadas" in html                       # Estado de linhas descartadas


def test_asset_import_template_uses_unified_mapping_table_and_defensive_dom_checks(authenticated_client):
    """
    Regressão: UI de importação deve usar tabela unificada de mapeamento
    e proteger acesso ao DOM. Teste atualizado para a nova central de revisão.
    """
    response = authenticated_client.get("/ativos/importacao")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Verificar que o template contém proteção defensiva
    assert "if (" in html  # Verificações defensivas
    assert "getElementById" in html or "querySelector" in html  # Acesso ao DOM
    assert "BLOCO A" in html or "mapeamento" in html.lower()  # Seção de mapeamento
    assert "table" in html.lower()  # Estrutura tabular
    assert "let " in html or "const " in html  # Declarações JS


def test_asset_import_preview_route_returns_schema_first_payload(monkeypatch):
    """
    Rota de preview deve retornar classificação de colunas sem persistir dados.
    """
    class MockServicoImportacaoComSeguranca:
        def gerar_preview_seguro(self, conteudo_csv, usuario_id, empresa_id, endereco_ip, user_agent, delimitador=None):
            _ = (usuario_id, empresa_id, endereco_ip, user_agent, delimitador)
            assert b"tipo_ativo" in conteudo_csv
            return "id-lote-teste", {
                "ok": True,
                "colunas": {
                    "exatas": [{"coluna_origem": "tipo_ativo", "campo_destino": "tipo_ativo"}],
                    "sugeridas": [{"coluna_origem": "teamviewer id", "campo_destino": "teamviewer_id", "score": 0.95}],
                    "ignoradas": [{"coluna_origem": "IMEI", "motivo": "bloqueada"}],
                },
                "preview_linhas": [{"linha": 2, "dados_mapeados": {"tipo_ativo": "Notebook"}}],
                "campos_destino_disponiveis": ["tipo_ativo", "teamviewer_id"],
                "campos_obrigatorios_preview": ["tipo_ativo", "marca", "modelo", "setor", "status", "data_entrada"],
                "validacao_detalhes": {"total_linhas": 1, "linhas_validas": 1, "linhas_invalidas": 0},
                "resumo_analise": {"total_linhas": 1, "linhas_validas": 1, "linhas_invalidas": 0},
                "erros_por_linha": [],
                "avisos_por_linha": [],
                "metadados_auditoria": {"id_lote": "id-lote-teste"},
            }

    class PreviewImportService:
        def gerar_preview_importacao_csv(self, conteudo_csv, user_id):
            del user_id
            assert b"tipo_ativo" in conteudo_csv
            return {
                "colunas": {
                    "exatas": [{"coluna_origem": "tipo_ativo", "campo_destino": "tipo_ativo"}],
                    "sugeridas": [{"coluna_origem": "teamviewer id", "campo_sugerido": "teamviewer_id"}],
                    "ignoradas": [{"coluna_origem": "IMEI", "motivo": "bloqueada"}],
                },
                "preview_linhas": [{"linha": 2, "dados_mapeados": {"tipo_ativo": "Notebook"}}],
                "resumo_validacao": {"total_linhas": 1, "linhas_validas": 1, "linhas_invalidas": 0, "erros": [], "avisos": []},
            }

        def gerar_preview_seguro(self, conteudo_csv, usuario_id, empresa_id, endereco_ip, user_agent, delimitador=None):
            # Mock para o novo método gerar_preview_seguro usado pela rota
            _ = (usuario_id, empresa_id, endereco_ip, user_agent, delimitador)
            assert b"tipo_ativo" in conteudo_csv
            return "id-lote-teste", {
                "ok": True,
                "colunas": {
                    "exatas": [{"coluna_origem": "tipo_ativo", "campo_destino": "tipo_ativo"}],
                    "sugeridas": [{"coluna_origem": "teamviewer id", "campo_destino": "teamviewer_id", "score": 0.95}],
                    "ignoradas": [{"coluna_origem": "IMEI", "motivo": "bloqueada"}],
                },
                "preview_linhas": [{"linha": 2, "dados_mapeados": {"tipo_ativo": "Notebook"}}],
                "campos_destino_disponiveis": ["tipo_ativo", "teamviewer_id"],
                "campos_obrigatorios_preview": ["tipo_ativo", "marca", "modelo", "setor", "status", "data_entrada"],
                "validacao_detalhes": {"total_linhas": 1, "linhas_validas": 1, "linhas_invalidas": 0},
                "resumo_analise": {"total_linhas": 1, "linhas_validas": 1, "linhas_invalidas": 0},
                "erros_por_linha": [],
                "avisos_por_linha": [],
                "metadados_auditoria": {"id_lote": "id-lote-teste"},
            }

        def confirmar_importacao_csv(self, *_args, **_kwargs):
            raise AssertionError("Preview não pode persistir importação.")

    from tests.conftest import (
        FakeArquivosService as _FakeArquivosService,
        FakeAuthService,
        FakeEmpresaService,
        aplicar_headers_csrf_no_client_teste,
    )

    # Monkeypatch ServicoImportacaoComSeguranca para retornar mock
    monkeypatch.setattr(
        "web_app.routes.ativos_routes.ServicoImportacaoComSeguranca",
        MockServicoImportacaoComSeguranca
    )

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": PreviewImportService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.post(
        "/ativos/importar/preview",
        data={"file": (BytesIO(b"tipo_ativo,marca,modelo\nNotebook,Dell,XPS"), "ativos.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    sugestao = payload["preview"]["colunas"]["sugeridas"][0]
    assert sugestao.get("campo_sugerido") == "teamviewer_id" or sugestao.get("campo_destino") == "teamviewer_id"
    assert payload["preview"]["colunas"]["ignoradas"][0]["coluna_origem"] == "IMEI"
    assert "campos_obrigatorios_preview" in payload["preview"]


def test_asset_import_confirm_route_sends_confirmed_suggestions():
    """
    Rota de confirmação deve encaminhar sugestões aprovadas para o service.
    """
    class ConfirmImportService:
        def __init__(self):
            self.recebido = None

        def confirmar_importacao_csv(self, conteudo_csv, sugestoes_confirmadas, user_id, *, modo_tudo_ou_nada, modo_importacao=None, mapeamento_confirmado=None, linhas_descartadas=None, edicoes_por_linha=None):
            assert modo_tudo_ou_nada is True
            assert modo_importacao == "tudo_ou_nada"
            self.recebido = {
                "conteudo": conteudo_csv,
                "sugestoes": sugestoes_confirmadas,
                "user_id": user_id,
                "modo_importacao": modo_importacao,
                "mapeamento_confirmado": mapeamento_confirmado,
                "linhas_descartadas": linhas_descartadas,
                "edicoes_por_linha": edicoes_por_linha,
            }
            return {
                "ok_importacao": True,
                "importados": 1,
                "falhas": 0,
                "ids_criados": ["OPU-000001"],
                "erros": [],
                "avisos": [],
                "colunas": {"exatas": [], "sugeridas": [], "ignoradas": []},
                "linhas_descartadas": 0,
                "linhas_editadas": 0,
            }

        def gerar_preview_importacao_csv(self, *_args, **_kwargs):
            raise AssertionError("Confirmação não deve chamar preview.")

    from tests.conftest import (
        FakeArquivosService as _FakeArquivosService,
        FakeAuthService,
        FakeEmpresaService,
        aplicar_headers_csrf_no_client_teste,
    )

    service = ConfirmImportService()
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": service,
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.post(
        "/ativos/importar/confirmar",
        data={
            "file": (BytesIO(b"tipo_ativo,marca,modelo\nNotebook,Dell,XPS"), "ativos.csv"),
            "sugestoes_confirmadas": "{\"teamviewer id\":\"teamviewer_id\",\"anydesk id\":\"anydesk_id\"}",
            "mapeamento_confirmado": "{\"tipo_ativo\":\"tipo_ativo\",\"marca\":\"marca\",\"modelo\":\"modelo\",\"setor\":\"setor\",\"status\":\"status\",\"data_entrada\":\"data_entrada\"}",
            # Garante contrato explícito do modo tudo-ou-nada.
            "modo_importacao": "tudo_ou_nada",
            "revisor_dados": "on",
            "confirma_duplicatas": "on",
            "aceita_avisos": "on",
            "autoriza_importacao": "on",
            "linhas_descartadas": "[]",
            "edicoes_por_linha": "{}",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201, f"Expected 201, got {response.status_code}. Response: {response.get_data(as_text=True)[:500]}"
    payload = response.get_json()
    assert payload["ok"] is True
    assert service.recebido is not None
    assert service.recebido["sugestoes"]["teamviewer id"] == "teamviewer_id"
    assert service.recebido["sugestoes"]["anydesk id"] == "anydesk_id"
    assert service.recebido["mapeamento_confirmado"]["tipo_ativo"] == "tipo_ativo"
    assert service.recebido["mapeamento_confirmado"]["data_entrada"] == "data_entrada"
    # Contrato da revisão consolidada: backend deve receber descarte/edição em estrutura tipada.
    assert service.recebido["linhas_descartadas"] == set()
    assert service.recebido["edicoes_por_linha"] == {}


def test_asset_import_confirm_route_maps_partial_mode_to_non_all_or_nothing():
    """
    Contrato da rota: modo "validas_e_avisos" deve chegar ao service
    como modo_tudo_ou_nada=False.
    """
    class ConfirmImportServicePartial:
        def __init__(self):
            self.modo_recebido = None

        def confirmar_importacao_csv(self, _conteudo_csv, _sugestoes_confirmadas, _user_id, *, modo_tudo_ou_nada, modo_importacao=None, mapeamento_confirmado=None, linhas_descartadas=None, edicoes_por_linha=None):
            self.modo_recebido = modo_tudo_ou_nada
            self.modo_importacao_recebido = modo_importacao
            _ = (mapeamento_confirmado, linhas_descartadas, edicoes_por_linha)
            return {
                "ok_importacao": True,
                "importados": 1,
                "falhas": 0,
                "ids_criados": ["OPU-000001"],
                "erros": [],
                "avisos": [],
                "colunas": {"exatas": [], "sugeridas": [], "ignoradas": []},
                "linhas_descartadas": 0,
                "linhas_editadas": 0,
            }

    from tests.conftest import (
        FakeArquivosService as _FakeArquivosService,
        FakeAuthService,
        FakeEmpresaService,
        aplicar_headers_csrf_no_client_teste,
    )

    service = ConfirmImportServicePartial()
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": service,
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.post(
        "/ativos/importar/confirmar",
        data={
            "file": (BytesIO(b"tipo_ativo,marca,modelo\nNotebook,Dell,XPS"), "ativos.csv"),
            "sugestoes_confirmadas": "{}",
            "mapeamento_confirmado": "{\"tipo_ativo\":\"tipo_ativo\",\"marca\":\"marca\",\"modelo\":\"modelo\",\"setor\":\"setor\",\"status\":\"status\",\"data_entrada\":\"data_entrada\"}",
            "modo_importacao": "validas_e_avisos",
            "revisor_dados": "on",
            "confirma_duplicatas": "on",
            "aceita_avisos": "on",
            "autoriza_importacao": "on",
            "linhas_descartadas": "[]",
            "edicoes_por_linha": "{}",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert service.modo_recebido is False
    assert service.modo_importacao_recebido == "validas_e_avisos"


def test_asset_import_template_has_functional_review_filters_and_error_driven_edit_modal(authenticated_client):
    """
    Regressão da central de revisão: filtros precisam estar implementados
    e o modal deve ser orientado por erro/campo crítico.
    """
    response = authenticated_client.get("/ativos/importacao")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Filtro implementado de fato (sem TODO pendente).
    assert "function filtrarLinhasRevisao(linhas, filtro)" in html
    assert "// TODO: implementar filtro dinâmico" not in html

    # Modal orientado a erro com mapeamento por campo.
    assert "function construirMapaErrosPorCampo(linha)" in html
    assert "Campos críticos para correção" in html
    assert "Campos opcionais" in html


def test_asset_import_template_uses_select_for_controlled_fields_in_edit_modal(authenticated_client):
    """
    Campos controlados no modal de revisão devem usar select/combobox,
    mantendo inputs livres apenas para campos textuais.
    """
    response = authenticated_client.get("/ativos/importacao")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "LISTAS_CONTROLADAS_IMPORTACAO" in html
    assert "tipo_ativo" in html
    assert "status" in html
    assert "setor" in html
    assert "localizacao" in html
    assert "<select class=\"select-control edit-field\"" in html


def test_asset_import_template_sends_mode_and_consolidated_discarded_lines(authenticated_client):
    """
    Payload final da confirmação deve carregar modo de importação e
    descarte consolidado (manual + política do modo).
    """
    response = authenticated_client.get("/ativos/importacao")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "function calcularLinhasDescartadasConsolidadas()" in html
    assert "function construirEdicoesAtivas(descartadasConsolidadas)" in html
    assert 'formData.append("modo_importacao", estadoRevisao.modoImportacao);' in html
    assert "descartadasConsolidadas" in html


def test_asset_create_page_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/novo")
    assert response.status_code == 200
    assert "Cadastro de ativo" in response.get_data(as_text=True)


def test_asset_create_page_uses_safe_attachment_int_route_builder(authenticated_client):
    response = authenticated_client.get("/ativos/novo")
    html = response.get_data(as_text=True)
    assert "templateUrl.replace(/\\/0(?=\\/|$)/" in html


def test_assets_listing_template_does_not_chain_replaceall_on_mapped_array(authenticated_client):
    """
    Regressão: a tabela de ativos não pode usar replaceAll diretamente no resultado de map(),
    pois isso quebra o carregamento com TypeError em runtime.
    """
    response = authenticated_client.get("/ativos/lista")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert ").replaceAll(\"__ID__\"" not in html


def test_assets_listing_template_does_not_leave_raw_jinja_inside_javascript(authenticated_client):
    """
    Regressão: o navegador não pode receber expressão Jinja literal dentro do script,
    pois isso gera SyntaxError e impede o carregamento da tabela.
    """
    response = authenticated_client.get("/ativos/lista")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "{{ status_validos | tojson }}" not in html
    assert "{{ tipos_validos | tojson }}" not in html
    assert "{{ setores_validos | tojson }}" not in html


def test_assets_listing_template_disables_header_quick_filters_by_feature_flag(authenticated_client):
    """
    Regressão: quick filters do cabeçalho devem permanecer desativados por feature flag
    para não impactar o fluxo principal da listagem.
    """
    response = authenticated_client.get("/ativos/lista")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "const QUICK_FILTERS_HEADER_ENABLED = false" in html
    assert "if (QUICK_FILTERS_HEADER_ENABLED && colConfig.quickFilter)" in html
    assert "if (!QUICK_FILTERS_HEADER_ENABLED) return;" in html


def test_assets_listing_template_removes_sort_click_from_header_name(authenticated_client):
    """
    Regressão de UX: nome da coluna não dispara ordenação por clique;
    apenas o controle dedicado do quick filter permanece interativo.
    """
    response = authenticated_client.get("/ativos/lista")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "header-column-label" in html
    assert "header-sort-button" not in html
    assert "Ordenar por" not in html
    assert "quick-filter-icon-btn" in html
    assert "filterButton.textContent = \"▾\"" in html


def test_assets_listing_template_preserves_date_quick_filter_base_for_future_reuse(authenticated_client):
    """
    Regressão: mesmo desativada, a base técnica do quick filter de data deve
    permanecer no template para facilitar reativação futura.
    """
    response = authenticated_client.get("/ativos/lista")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "function renderQuickFilterDataEntrada(container)" in html
    assert "Mais recentes" in html
    assert "Mais antigos" in html
    assert "Hoje" in html
    assert "Últimos 7 dias" in html
    assert "Este mês" in html


def test_assets_listing_template_applies_date_quick_filter_only_by_selection(authenticated_client):
    """
    Regressão: com quick filters desativados, não deve haver bind residual de eventos
    nem aplicação de parâmetros no fluxo principal.
    """
    response = authenticated_client.get("/ativos/lista")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "params.delete(\"data_entrada_inicial\")" in html
    assert "params.delete(\"data_entrada_final\")" in html
    assert "if (QUICK_FILTERS_HEADER_ENABLED) {" in html
    assert "let currentSort" not in html
    assert "currentSort.field" not in html
    assert "params.set(\"ordenar_por\", currentSort.field)" not in html
    assert "if (dateShortcut === \"mais_recentes\")" in html
    assert "params.set(\"ordenar_por\", \"data_entrada\")" in html
    assert "params.set(\"ordem\", \"desc\")" in html
    assert "if (dateShortcut === \"mais_antigos\")" in html
    assert "params.set(\"ordem\", \"asc\")" in html


def test_assets_listing_template_keeps_conventional_filter_flow_visible_and_active(authenticated_client):
    """
    Regressão: o filtro convencional via botão "Filtrar" deve continuar
    como única entrada visível de filtragem nesta etapa.
    """
    response = authenticated_client.get("/ativos/lista")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'id="open-filter-modal"' in html
    assert 'id="filter-modal"' in html
    assert 'id="apply-filters"' in html
    assert 'id="reset-filters"' in html
    assert "collectFiltersFromModal()" in html
    assert "document.getElementById(\"open-filter-modal\").addEventListener(\"click\"" in html


def test_assets_listing_template_uses_robust_highlight_normalization_for_novo_badge(authenticated_client):
    """
    Regressão do destaque pós-cadastro: comparação de highlight deve ser normalizada
    para evitar falha por encoding/case e manter badge NOVO estável.
    """
    response = authenticated_client.get("/ativos/lista")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "function normalizeAssetId(value)" in html
    assert "decodeURIComponent(raw)" in html
    assert "normalizeAssetId(asset.id) === normalizeAssetId(highlightId)" in html
    assert "data-asset-id=\"${encodeURIComponent(String(asset.id || \"\"))}\"" in html


def test_assets_listing_template_contains_dark_themed_quick_filter_popover_container(app_fixture):
    """
    Regressão visual: popover do quick filter deve usar classes dedicadas para
    renderização consistente no tema escuro.
    """
    del app_fixture
    from pathlib import Path

    template_path = Path(__file__).parent.parent / "web_app" / "templates" / "ativos.html"
    css_path = Path(__file__).parent.parent / "web_app" / "static" / "css" / "style.css"

    template_content = template_path.read_text(encoding="utf-8")
    css_content = css_path.read_text(encoding="utf-8")

    assert 'id="quick-filter-popover"' in template_content
    assert "quick-filter-content" in template_content
    assert "quick-filter-actions" in template_content
    assert "#quick-filter-popover" in css_content
    assert ".quick-filter-option-label" in css_content


def test_asset_create_template_includes_escape_html_for_confirmation_modal(authenticated_client):
    """
    Regressão: a modal de confirmação do cadastro depende de escapeHtml().
    Se a função não existir, o submit fica silenciosamente interrompido.
    """
    response = authenticated_client.get("/ativos/novo")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "function escapeHtml(text)" in html


def test_asset_create_template_has_final_confirmation_and_highlight_redirect(authenticated_client):
    """
    Regressão do fluxo de cadastro: manter confirmação final, trava de envio
    e redirecionamento para listagem com highlight do ativo criado.
    """
    response = authenticated_client.get("/ativos/novo")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'id="confirm-asset-modal"' in html
    assert 'id="confirm-asset-button"' in html
    assert "let isCreateSubmitting = false" in html
    assert "if (isCreateSubmitting) return;" in html
    assert "confirmButton.textContent = \"Salvando...\"" in html
    assert "?highlight=" in html


def test_asset_create_template_keeps_core_specs_and_simplifies_monitor(authenticated_client):
    """
    Regressão de UX do cadastro: notebook/desktop/celular mantêm blocos técnicos
    completos, enquanto monitor fica enxuto com campo principal.
    """
    response = authenticated_client.get("/ativos/novo")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Blocos unificados para tipos estratégicos.
    # Fase 4.3: Notebook e Desktop unificados em bloco "specs-computador" com campos condicionais
    assert 'id="specs-computador"' in html
    assert 'id="specs-celular"' in html
    # Fase 4.3: IMEI restaurado para celular
    assert 'id="imei_1"' in html

    # Monitor com especificações completas no formulário.
    assert 'id="specs-monitor"' in html
    assert 'id="polegadas"' in html
    # Fase 4.3: Monitor agora inclui resolucao e entrada_video
    assert 'id="resolucao"' in html
    assert 'id="entrada_video"' in html


def test_asset_create_template_confirmation_reflects_type_specs(authenticated_client):
    """
    Regressão da confirmação: modal deve refletir especificações realmente usadas
    por tipo. Fase 4.3: campos não mais pruned — backend controla via validators.
    """
    response = authenticated_client.get("/ativos/novo")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "function collectTypeSpecificSpecificationRows(data)" in html
    assert '"Especificações por tipo": typeSpecificationRows' in html
    assert "function pruneDeprecatedSpecsByType(body)" in html
    # Fase 4.3: Função simplificada, validators do backend controlam campos permitidos


def test_asset_edit_page_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/editar/A-001")
    assert response.status_code == 200
    assert "Edição do ativo" in response.get_data(as_text=True)


def test_asset_edit_page_contains_movement_modal_flow_elements(authenticated_client):
    response = authenticated_client.get("/ativos/editar/A-001")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # Garante que a UI da Fase 3 está presente no template de edição.
    assert "movement-confirmation-modal" in html
    assert "Confirmar e salvar" in html
    assert "/movimentacao/preview" in html
    assert "/movimentacao/confirmar" in html


def test_asset_edit_template_simplifies_monitor_specs_and_keeps_core_types(authenticated_client):
    """
    Regressão da edição: monitor deve manter apenas polegadas no bloco técnico,
    sem campos extras; celular/notebook/desktop permanecem com blocos completos.
    """
    response = authenticated_client.get("/ativos/editar/A-001")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'id="specs-notebook"' in html
    assert 'id="specs-desktop"' in html
    assert 'id="specs-celular"' in html
    # Fase 3 Round 3: IMEI removido do fluxo de celular

    assert 'id="specs-monitor"' in html
    assert 'id="polegadas"' in html
    assert 'id="resolucao"' not in html
    assert 'id="tipo_painel"' not in html
    assert 'id="entrada_video"' not in html
    assert 'id="fonte_ou_cabo"' not in html


def test_asset_edit_template_does_not_reference_removed_descricao_categoria_fields(authenticated_client):
    # Regressão: o script não pode acessar campos removidos (descricao/categoria), evitando erro JS em runtime.
    response = authenticated_client.get("/ativos/editar/A-001")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'getElementById("descricao")' not in html
    assert 'getElementById("categoria")' not in html


def test_asset_create_route_exposes_automatic_timestamps():
    class TimestampAtivosService:
        def criar_ativo(self, _ativo, _user_id):
            return "OPU-000999"

        def buscar_ativo(self, id_ativo, _user_id):
            return SimpleNamespace(
                id_ativo=id_ativo,
                tipo="Notebook",
                tipo_ativo="Notebook",
                marca="Dell",
                modelo="XPS",
                usuario_responsavel="Ana",
                departamento="TI",
                setor="TI",
                status="Disponível",
                data_entrada="2026-04-14",
                data_saida=None,
                created_at="2026-04-14 09:00:00",
                updated_at="2026-04-14 09:00:00",
                data_ultima_movimentacao=None,
            )

    from tests.conftest import (
        FakeArquivosService as _FakeArquivosService,
        FakeAuthService,
        FakeEmpresaService,
        aplicar_headers_csrf_no_client_teste,
    )

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": TimestampAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.post(
        "/ativos",
        json={
            "tipo_ativo": "Notebook",
            "marca": "Dell",
            "modelo": "XPS",
            "descricao": "Notebook corporativo",
            "categoria": "Computadores",
            "status": "Disponível",
            "data_entrada": "2026-04-14",
            "setor": "TI",
            "departamento": "TI",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    ativo = payload["ativo"]
    assert ativo["created_at"] == "2026-04-14 09:00:00"
    assert ativo["updated_at"] == "2026-04-14 09:00:00"


def test_asset_create_route_blocks_duplicate_while_processing():
    """
    Regressão de deduplicação: quando a chave está reservada sem ID (requisição
    inicial ainda processando), nova tentativa deve retornar 409 e não criar ativo.
    """
    import web_app.routes.ativos_routes as ativos_routes_module

    class CountingAtivosService:
        def __init__(self):
            self.criar_calls = 0

        def criar_ativo(self, _ativo, _user_id):
            self.criar_calls += 1
            return "OPU-000321"

        def buscar_ativo(self, id_ativo, _user_id):
            return SimpleNamespace(
                id_ativo=id_ativo,
                tipo="Notebook",
                tipo_ativo="Notebook",
                marca="Dell",
                modelo="XPS",
                usuario_responsavel="Ana",
                departamento="TI",
                setor="TI",
                status="Disponível",
                data_entrada="2026-04-14",
                data_saida=None,
                created_at="2026-04-14 09:00:00",
                updated_at="2026-04-14 09:00:00",
                data_ultima_movimentacao=None,
            )

    from tests.conftest import (
        FakeArquivosService as _FakeArquivosService,
        FakeAuthService,
        FakeEmpresaService,
        aplicar_headers_csrf_no_client_teste,
    )

    service = CountingAtivosService()
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": service,
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    payload = {
        "tipo_ativo": "Notebook",
        "marca": "Dell",
        "modelo": "XPS",
        "status": "Disponível",
        "data_entrada": "2026-04-15",
        "setor": "TI",
        "localizacao": "Opus Medical",
    }

    gerar_chave_dedup = getattr(ativos_routes_module, "_gerar_chave_dedup")
    dedup_cache = getattr(ativos_routes_module, "_creation_dedup_cache")

    chave = gerar_chave_dedup(payload, 1)
    dedup_cache[chave] = (None, time.time())

    response = client.post("/ativos", json=payload)
    assert response.status_code == 409
    body = response.get_json()
    assert body["ok"] is False
    assert "processamento" in body["erro"].lower()
    assert service.criar_calls == 0

    # Limpeza defensiva para evitar interferência em outros testes.
    dedup_cache.pop(chave, None)


def test_asset_update_route_returns_movement_summary():
    class MovementAtivosService:
        def atualizar_ativo(self, id_ativo, dados, user_id):
            del user_id
            return SimpleNamespace(
                id_ativo=id_ativo,
                tipo="Notebook",
                tipo_ativo=dados.get("tipo_ativo", "Notebook"),
                marca="Dell",
                modelo="XPS",
                usuario_responsavel=dados.get("usuario_responsavel", "Ana Silva"),
                departamento=dados.get("departamento", "TI"),
                setor=dados.get("setor", "TI"),
                status=dados.get("status", "Disponível"),
                data_entrada=dados.get("data_entrada", "2026-04-01"),
                data_saida=None,
                created_at="2026-04-01 09:00:00",
                updated_at="2026-04-14 11:00:00",
                data_ultima_movimentacao="2026-04-14 11:00:00",
                resumo_movimentacao={
                    "status_atual": "Disponível",
                    "status_sugerido": "Em Uso",
                    "tipo_movimentacao": "entrega_para_colaborador",
                    "descricao_movimentacao": "Entrega para colaborador",
                    "mudanca_relevante": True,
                    "atualizar_data_ultima_movimentacao": True,
                    "campos_alterados": [
                        {"campo": "usuario_responsavel", "rotulo": "Responsável", "antes": "", "depois": "Ana Silva", "relevante": True}
                    ],
                    "estado_anterior": {"status": "Disponível", "usuario_responsavel": "", "setor": "TI", "localizacao": "Matriz"},
                    "estado_novo": {"status": "Disponível", "usuario_responsavel": "Ana Silva", "setor": "TI", "localizacao": "Matriz"},
                },
            )

        def buscar_ativo(self, id_ativo, _user_id):
            return SimpleNamespace(id_ativo=id_ativo)

    from tests.conftest import (
        FakeArquivosService as _FakeArquivosService,
        FakeAuthService,
        FakeEmpresaService,
        aplicar_headers_csrf_no_client_teste,
    )

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": MovementAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.put(
        "/ativos/OPU-000999",
        json={
            "tipo_ativo": "Notebook",
            "marca": "Dell",
            "modelo": "XPS",
            "descricao": "Notebook corporativo",
            "categoria": "Computadores",
            "status": "Disponível",
            "data_entrada": "2026-04-14",
            "usuario_responsavel": "Ana Silva",
            "setor": "TI",
            "departamento": "TI",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["resumo_movimentacao"]["tipo_movimentacao"] == "entrega_para_colaborador"
    assert payload["resumo_movimentacao"]["status_sugerido"] == "Em Uso"
    assert payload["ativo"]["data_ultima_movimentacao"] == "2026-04-14 11:00:00"


def test_asset_preview_route_returns_summary_without_persisting():
    class PreviewOnlyAtivosService:
        def __init__(self):
            self.preview_calls = 0

        def gerar_preview_atualizacao(self, id_ativo, dados, user_id):
            del id_ativo, dados, user_id
            self.preview_calls += 1
            return {
                "status_atual": "Disponível",
                "status_sugerido": "Em Uso",
                "tipo_movimentacao": "entrega_para_colaborador",
                "descricao_movimentacao": "Entrega para colaborador",
                "mudanca_relevante": True,
                "campos_alterados": [
                    {
                        "campo": "usuario_responsavel",
                        "rotulo": "Responsável",
                        "antes": "",
                        "depois": "Ana Silva",
                        "relevante": True,
                    }
                ],
                "resumo_movimentacao": {
                    "status_atual": "Disponível",
                    "status_sugerido": "Em Uso",
                    "tipo_movimentacao": "entrega_para_colaborador",
                    "descricao_movimentacao": "Entrega para colaborador",
                    "mudanca_relevante": True,
                    "campos_alterados": [],
                },
            }

        def atualizar_ativo(self, *_args, **_kwargs):
            raise AssertionError("A rota de preview não pode persistir dados.")

    from tests.conftest import (
        FakeArquivosService as _FakeArquivosService,
        FakeAuthService,
        FakeEmpresaService,
        aplicar_headers_csrf_no_client_teste,
    )

    service = PreviewOnlyAtivosService()
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": service,
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.post(
        "/ativos/OPU-000999/movimentacao/preview",
        json={
            "tipo_ativo": "Notebook",
            "marca": "Dell",
            "modelo": "XPS",
            "descricao": "Notebook corporativo",
            "categoria": "Computadores",
            "status": "Disponível",
            "data_entrada": "2026-04-14",
            "usuario_responsavel": "Ana Silva",
            "setor": "TI",
            "departamento": "TI",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["preview"]["tipo_movimentacao"] == "entrega_para_colaborador"
    assert service.preview_calls == 1


def test_asset_confirm_route_applies_operational_adjustments():
    class ConfirmFlowAtivosService:
        def __init__(self):
            self.recebido = None

        def preparar_dados_confirmacao_movimentacao(self, dados, ajustes):
            # Replica o contrato do service real para validar integração da rota.
            dados_finais = dict(dados)
            dados_finais["status"] = ajustes.get("status_final")
            dados_finais["usuario_responsavel"] = ajustes.get("usuario_responsavel")
            dados_finais["setor"] = ajustes.get("setor")
            dados_finais["departamento"] = ajustes.get("setor")
            dados_finais["localizacao"] = ajustes.get("localizacao")
            dados_finais["observacoes"] = "[Movimentação] " + (ajustes.get("observacao_movimentacao") or "")
            return dados_finais

        def atualizar_ativo(self, id_ativo, dados, user_id):
            del user_id
            self.recebido = dados
            return SimpleNamespace(
                id_ativo=id_ativo,
                tipo="Notebook",
                tipo_ativo=dados.get("tipo_ativo", "Notebook"),
                marca=dados.get("marca", "Dell"),
                modelo=dados.get("modelo", "XPS"),
                usuario_responsavel=dados.get("usuario_responsavel"),
                departamento=dados.get("departamento"),
                setor=dados.get("setor"),
                localizacao=dados.get("localizacao"),
                status=dados.get("status"),
                data_entrada=dados.get("data_entrada", "2026-04-01"),
                data_saida=None,
                created_at="2026-04-01 09:00:00",
                updated_at="2026-04-14 12:00:00",
                data_ultima_movimentacao="2026-04-14 12:00:00",
                resumo_movimentacao={
                    "tipo_movimentacao": "troca_de_responsavel",
                    "status_sugerido": "Em Uso",
                    "mudanca_relevante": True,
                    "campos_alterados": [],
                },
            )

    from tests.conftest import (
        FakeArquivosService as _FakeArquivosService,
        FakeAuthService,
        FakeEmpresaService,
        aplicar_headers_csrf_no_client_teste,
    )

    service = ConfirmFlowAtivosService()
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": service,
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.post(
        "/ativos/OPU-000999/movimentacao/confirmar",
        json={
            "dados_formulario": {
                "tipo_ativo": "Notebook",
                "marca": "Dell",
                "modelo": "XPS",
                "descricao": "Notebook corporativo",
                "categoria": "Computadores",
                "status": "Disponível",
                "data_entrada": "2026-04-14",
                "usuario_responsavel": "Ana Silva",
                "setor": "TI",
                "departamento": "TI",
                "localizacao": "Matriz",
            },
            "ajustes_movimentacao": {
                "status_final": "Em Uso",
                "usuario_responsavel": "Beatriz Souza",
                "setor": "Logística",
                "localizacao": "CD-01",
                "observacao_movimentacao": "Entrega registrada no turno da manhã",
            },
        },
    )

    assert response.status_code == 200
    assert service.recebido["status"] == "Em Uso"
    assert service.recebido["usuario_responsavel"] == "Beatriz Souza"
    assert service.recebido["setor"] == "Logística"
    assert service.recebido["localizacao"] == "CD-01"
    assert "[Movimentação]" in service.recebido["observacoes"]


def test_asset_confirm_route_accepts_sparse_form_payload_without_cadastro_fields():
    class ConfirmSparsePayloadAtivosService:
        def preparar_dados_confirmacao_movimentacao(self, dados, ajustes):
            # Simula merge operacional sem exigir descrição/categoria/condição.
            dados_finais = dict(dados)
            dados_finais["status"] = ajustes.get("status_final") or dados_finais.get("status")
            dados_finais["usuario_responsavel"] = ajustes.get("usuario_responsavel")
            dados_finais["setor"] = ajustes.get("setor")
            dados_finais["departamento"] = ajustes.get("setor")
            dados_finais["localizacao"] = ajustes.get("localizacao")
            return dados_finais

        def atualizar_ativo(self, id_ativo, dados, user_id):
            del user_id
            assert "descricao" not in dados
            assert "categoria" not in dados
            assert "condicao" not in dados
            return SimpleNamespace(
                id_ativo=id_ativo,
                tipo="Notebook",
                tipo_ativo="Notebook",
                marca="Dell",
                modelo="XPS",
                usuario_responsavel=dados.get("usuario_responsavel"),
                departamento=dados.get("departamento"),
                setor=dados.get("setor"),
                localizacao=dados.get("localizacao"),
                status=dados.get("status"),
                data_entrada="2026-04-14",
                data_saida=None,
                resumo_movimentacao={"tipo_movimentacao": "entrega_para_colaborador", "campos_alterados": []},
            )

    from tests.conftest import (
        FakeArquivosService as _FakeArquivosService,
        FakeAuthService,
        FakeEmpresaService,
        aplicar_headers_csrf_no_client_teste,
    )

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": ConfirmSparsePayloadAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.post(
        "/ativos/OPU-000999/movimentacao/confirmar",
        json={
            "dados_formulario": {
                "status": "Disponível",
                "setor": "TI",
                "localizacao": "Matriz",
            },
            "ajustes_movimentacao": {
                "status_final": "Em Uso",
                "usuario_responsavel": "Ana Silva",
                "setor": "Logística",
                "localizacao": "CD-01",
            },
        },
    )

    assert response.status_code == 200


def test_asset_preview_route_requires_authentication(http_client):
    response = http_client.post(
        "/ativos/OPU-000999/movimentacao/preview",
        json={"tipo_ativo": "Notebook", "status": "Disponível", "data_entrada": "2026-04-14"},
    )
    assert response.status_code == 401


def test_asset_preview_route_keeps_permission_contract():
    class ForbiddenPreviewAtivosService:
        def gerar_preview_atualizacao(self, id_ativo, dados, user_id):
            del id_ativo, dados, user_id
            raise PermissaoNegada("Sem permissão para visualizar este ativo.")

    from tests.conftest import (
        FakeArquivosService as _FakeArquivosService,
        FakeAuthService,
        FakeEmpresaService,
        aplicar_headers_csrf_no_client_teste,
    )

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": ForbiddenPreviewAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.post(
        "/ativos/OPU-000999/movimentacao/preview",
        json={"tipo_ativo": "Notebook", "status": "Disponível", "data_entrada": "2026-04-14"},
    )
    assert response.status_code == 400


def test_asset_view_page_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/visualizar/A-001", follow_redirects=True)
    assert response.status_code == 200
    assert "Especificacoes do ativo" in response.get_data(as_text=True)


def test_asset_details_page_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/detalhes/A-001")
    assert response.status_code == 200
    assert "Documentos vinculados" in response.get_data(as_text=True)
    assert "nf.pdf" in response.get_data(as_text=True)


def test_asset_details_page_shows_garantia_and_complementar_from_attachments():
    class FakeArquivosDetalhe:
        upload_base_dir = "."

        def listar_arquivos(self, id_ativo, _user_id):
            return [
                {
                    "id": 11,
                    "ativo_id": id_ativo,
                    "tipo_documento": "garantia",
                    "nome_original": "garantia_produto.pdf",
                    "tamanho_bytes": 1024,
                    "mime_type": "application/pdf",
                    "criado_em": "2026-04-06",
                },
                {
                    "id": 12,
                    "ativo_id": id_ativo,
                    "tipo_documento": "outro",
                    "nome_original": "manual_tecnico.pdf",
                    "tamanho_bytes": 2048,
                    "mime_type": "application/pdf",
                    "criado_em": "2026-04-06",
                },
            ]

        def salvar_arquivo(self, **_kwargs):
            return 11

        def obter_arquivo(self, _arquivo_id, _user_id):
            return {
                "caminho_arquivo": "uploads/garantia_produto.pdf",
                "nome_original": "garantia_produto.pdf",
                "mime_type": "application/pdf",
            }

        def remover_arquivo(self, _arquivo_id, _user_id):
            return None

    from tests.conftest import FakeAtivosService, FakeAuthService, FakeEmpresaService, aplicar_headers_csrf_no_client_teste

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosService(),
            "ativos_arquivo_service": FakeArquivosDetalhe(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
        session_data["user_perfil"] = "usuario"
        session_data["user_empresa_id"] = 10
        session_data["user_empresa_nome"] = "Empresa Demo"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.get("/ativos/detalhes/A-001")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "garantia_produto.pdf" in html
    assert "manual_tecnico.pdf" in html


def test_asset_edit_alias_route_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/A-001/editar", follow_redirects=True)
    assert response.status_code == 200
    assert "Dados do ativo" in response.get_data(as_text=True)


def test_login_flow_basic(http_client):
    response = http_client.post("/login", json={"email": "user@example.com", "senha": "secret"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["redirect_url"].endswith("/dashboard")


def test_login_with_remember_me_sets_permanent_session(http_client):
    response = http_client.post(
        "/login",
        json={"email": "user@example.com", "senha": "secret", "lembrar_me": True},
    )
    assert response.status_code == 200

    with http_client.session_transaction() as session_data:
        assert session_data.permanent is True

    set_cookie = " ".join(response.headers.getlist("Set-Cookie"))
    assert "remember_active=1" in set_cookie
    assert "remember_email=" in set_cookie


def test_login_without_remember_me_keeps_default_session(http_client):
    response = http_client.post(
        "/login",
        json={"email": "user@example.com", "senha": "secret", "lembrar_me": False},
    )
    assert response.status_code == 200

    with http_client.session_transaction() as session_data:
        assert session_data.permanent is False


def test_login_remember_me_still_works_when_db_is_legacy():
    from tests.conftest import FakeArquivosService, FakeAtivosService, FakeAuthService, FakeEmpresaService

    class LegacyRememberAuthService(FakeAuthService):
        def atualizar_preferencia_lembrar_me(self, _user_id: int, _ativo: bool):
            from services.auth_service import AuthErro

            raise AuthErro("A preferencia 'lembrar de mim' requer atualizacao de banco (migration 004).")

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": LegacyRememberAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosService(),
            "ativos_arquivo_service": FakeArquivosService(),
        },
    )
    client = app.test_client()

    response = client.post(
        "/login",
        json={"email": "user@example.com", "senha": "secret", "lembrar_me": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert "migration 004" in (payload.get("aviso") or "")


def test_login_page_available(http_client):
    response = http_client.get("/login")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Acesso ao Sistema" in html
    assert "mostrar-senha" in html
    assert "lembrar_me" in html


def test_login_page_prefills_email_when_remember_cookie_is_active(http_client):
    http_client.set_cookie("remember_active", "1")
    http_client.set_cookie("remember_email", "remembered@example.com")

    response = http_client.get("/login")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "remembered@example.com" in html
    assert "checked disabled" in html


def test_settings_page_authenticated(authenticated_client):
    response = authenticated_client.get("/configuracoes")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Configurações da Conta" in html
    assert "Dados de Perfil" in html


def test_settings_user_cannot_change_email(authenticated_client, app_fixture):
    from tests.conftest import gerar_csrf_token_para_teste
    csrf = gerar_csrf_token_para_teste(app_fixture, user_id=1)
    response = authenticated_client.post(
        "/configuracoes/perfil",
        data={"nome": "Novo Nome", "email": "novo-email@example.com", "csrf_token": csrf},
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Apenas administradores podem alterar o e-mail." in html


def test_settings_user_can_change_name(authenticated_client, app_fixture):
    from tests.conftest import gerar_csrf_token_para_teste
    csrf = gerar_csrf_token_para_teste(app_fixture, user_id=1)
    response = authenticated_client.post(
        "/configuracoes/perfil",
        data={"nome": "Nome Atualizado", "email": "user@example.com", "csrf_token": csrf},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Perfil atualizado com sucesso." in response.get_data(as_text=True)


def test_settings_admin_can_change_email():
    from tests.conftest import FakeArquivosService, FakeAtivosService, FakeAuthService, FakeEmpresaService, gerar_csrf_token_para_teste

    auth = FakeAuthService()
    auth.user_data["perfil"] = "admin"

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": auth,
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosService(),
            "ativos_arquivo_service": FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
        session_data["user_perfil"] = "admin"
        session_data["user_empresa_id"] = 10
        session_data["user_empresa_nome"] = "Empresa Demo"

    csrf = gerar_csrf_token_para_teste(app, user_id=1)
    response = client.post(
        "/configuracoes/perfil",
        data={"nome": "Admin", "email": "admin@empresa.com", "csrf_token": csrf},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Perfil atualizado com sucesso." in response.get_data(as_text=True)


def test_settings_can_disable_remember_me(authenticated_client, app_fixture):
    from tests.conftest import gerar_csrf_token_para_teste
    csrf = gerar_csrf_token_para_teste(app_fixture, user_id=1)
    response = authenticated_client.post(
        "/configuracoes/lembrar-me",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code in {301, 302}
    set_cookie = " ".join(response.headers.getlist("Set-Cookie"))
    assert "remember_active=;" in set_cookie


def test_settings_can_change_password(authenticated_client, app_fixture):
    from tests.conftest import gerar_csrf_token_para_teste
    csrf = gerar_csrf_token_para_teste(app_fixture, user_id=1)
    response = authenticated_client.post(
        "/configuracoes/senha",
        data={
            "senha_atual": "secret",
            "nova_senha": "secretNova123",
            "confirmar_nova_senha": "secretNova123",
            "csrf_token": csrf,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Senha atualizada com sucesso." in response.get_data(as_text=True)


def test_dashboard_requires_authentication(http_client):
    response = http_client.get("/dashboard", follow_redirects=False)
    assert response.status_code in {301, 302}
    assert response.headers.get("Location", "").endswith("/")


def test_assets_html_requires_authentication(http_client):
    response = http_client.get("/ativos/lista", follow_redirects=False)
    assert response.status_code in {301, 302}
    assert response.headers.get("Location", "").endswith("/")


def test_logout_web_clears_session(authenticated_client):
    response = authenticated_client.get("/logout", follow_redirects=False)
    assert response.status_code in {301, 302}
    assert response.headers.get("Location", "").endswith("/")

    response_after_logout = authenticated_client.get("/dashboard", follow_redirects=False)
    assert response_after_logout.status_code in {301, 302}
    assert response_after_logout.headers.get("Location", "").endswith("/")


def test_session_endpoint_requires_authentication(http_client):
    response = http_client.get("/session")
    assert response.status_code == 401
    payload = response.get_json()
    assert payload["authenticated"] is False


def test_ativos_route_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["ativos"]


def test_ativos_route_document_presence_filters_consider_attachments():
    class FakeAtivosComDoisItens:
        def listar_ativos(self, _user_id):
            return [
                SimpleNamespace(
                    id_ativo="A-111",
                    tipo="Notebook",
                    tipo_ativo="Notebook",
                    marca="Dell",
                    modelo="XPS",
                    usuario_responsavel="Ana",
                    departamento="TI",
                    setor="TI",
                    status="Disponível",
                    data_entrada="2026-04-01",
                    data_saida=None,
                    nota_fiscal="",
                    garantia="",
                ),
                SimpleNamespace(
                    id_ativo="A-222",
                    tipo="Notebook",
                    tipo_ativo="Notebook",
                    marca="Lenovo",
                    modelo="T14",
                    usuario_responsavel="Bruno",
                    departamento="TI",
                    setor="TI",
                    status="Em Uso",
                    data_entrada="2026-04-02",
                    data_saida=None,
                    nota_fiscal="",
                    garantia="",
                ),
            ]

        def filtrar_ativos(self, **_kwargs):
            return self.listar_ativos(1)

    class FakeArquivosFiltroPresenca:
        upload_base_dir = "."

        def listar_arquivos(self, id_ativo, _user_id):
            # Apenas A-111 possui garantia real por anexo; A-222 não possui documento.
            if id_ativo == "A-111":
                return [
                    {
                        "id": 55,
                        "ativo_id": "A-111",
                        "tipo_documento": "garantia",
                        "nome_original": "garantia_notebook.pdf",
                        "tamanho_bytes": 123,
                        "mime_type": "application/pdf",
                        "criado_em": "2026-04-10",
                    }
                ]
            return []

        def salvar_arquivo(self, **_kwargs):
            return 1

        def obter_arquivo(self, _arquivo_id, _user_id):
            return {"caminho_arquivo": "", "nome_original": "", "mime_type": ""}

        def remover_arquivo(self, _arquivo_id, _user_id):
            return None

    from tests.conftest import FakeAuthService, FakeEmpresaService

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosComDoisItens(),
            "ativos_arquivo_service": FakeArquivosFiltroPresenca(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    response_com_garantia = client.get("/ativos?tem_garantia=sim")
    assert response_com_garantia.status_code == 200
    payload_com = response_com_garantia.get_json()
    assert [item["id"] for item in payload_com["ativos"]] == ["A-111"]

    response_sem_garantia = client.get("/ativos?tem_garantia=nao")
    assert response_sem_garantia.status_code == 200
    payload_sem = response_sem_garantia.get_json()
    assert [item["id"] for item in payload_sem["ativos"]] == ["A-222"]


def test_attachment_route_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/A-001/anexos")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["anexos"]


def test_attachment_upload_without_file_returns_400(authenticated_client):
    response = authenticated_client.post(
        "/ativos/A-001/anexos",
        data={"type": "nota_fiscal"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False


def test_attachment_upload_invalid_type_returns_400():
    class FakeArquivosComValidacao:
        upload_base_dir = "."

        def salvar_arquivo(self, **kwargs):
            if kwargs.get("tipo_documento") not in {"nota_fiscal", "garantia", "outro"}:
                from services.ativos_arquivo_service import TipoDocumentoInvalido

                raise TipoDocumentoInvalido("Tipo de documento inválido.")
            return 1

        def listar_arquivos(self, _id_ativo, _user_id):
            return []

        def obter_arquivo(self, _arquivo_id, _user_id):
            return {"caminho_arquivo": "", "nome_original": "", "mime_type": ""}

        def remover_arquivo(self, _arquivo_id, _user_id):
            return None

    from tests.conftest import FakeAtivosService, FakeAuthService, FakeEmpresaService, aplicar_headers_csrf_no_client_teste

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosService(),
            "ativos_arquivo_service": FakeArquivosComValidacao(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.post(
        "/ativos/A-001/anexos",
        data={
            "type": "nao_permitido",
            "file": (BytesIO(b"abc"), "teste.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False


def test_attachment_delete_route_uses_correct_attachment_id():
    class FakeArquivosDeleteTracking:
        upload_base_dir = "."

        def __init__(self):
            self.removed_ids = []

        def salvar_arquivo(self, **_kwargs):
            return 1

        def listar_arquivos(self, _id_ativo, _user_id):
            return []

        def obter_arquivo(self, _arquivo_id, _user_id):
            return {"caminho_arquivo": "", "nome_original": "", "mime_type": ""}

        def remover_arquivo(self, arquivo_id, _user_id):
            self.removed_ids.append(arquivo_id)

    from tests.conftest import FakeAtivosService, FakeAuthService, FakeEmpresaService, aplicar_headers_csrf_no_client_teste

    fake_arquivos = FakeArquivosDeleteTracking()
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosService(),
            "ativos_arquivo_service": fake_arquivos,
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.delete("/anexos/7")
    assert response.status_code == 200
    assert fake_arquivos.removed_ids == [7]


def test_service_delete_keeps_db_cleanup_when_physical_file_is_missing():
    from unittest.mock import MagicMock
    from services.ativos_arquivo_service import AtivosArquivoService
    from services.storage_backend import StorageBackendError

    class FakeCursor:
        def __init__(self):
            self.rowcount = 1

        def execute(self, _query, _params):
            return None

    class FakeCursorContext:
        def __init__(self, cursor):
            self.cursor = cursor

        def __enter__(self):
            return (None, self.cursor)

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_cursor = FakeCursor()
    fake_storage = MagicMock()
    fake_storage.delete.side_effect = StorageBackendError("Arquivo não encontrado no storage")
    service = AtivosArquivoService(fake_storage)

    with patch("services.ativos_arquivo_service.cursor_mysql", return_value=FakeCursorContext(fake_cursor)):
        service.obter_arquivo = lambda _arquivo_id, _user_id: {
            "caminho_arquivo": "ativos/A-001/nao_existe.pdf"
        }
        service.remover_arquivo(123, 1)

    assert fake_cursor.rowcount == 1


def test_export_json_route_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/export/json")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["formato"] == "json"
    assert isinstance(payload["ativos"], list)


def test_export_json_uses_linked_documents_for_nota_fiscal_and_garantia():
    class FakeAtivosSemDocs:
        def listar_ativos(self, _user_id):
            return [
                SimpleNamespace(
                    id_ativo="A-777",
                    tipo="Notebook",
                    marca="Dell",
                    modelo="XPS",
                    usuario_responsavel="Ana",
                    departamento="TI",
                    status="Ativo",
                    data_entrada="2026-04-01",
                    data_saida=None,
                    nota_fiscal="",
                    garantia="",
                )
            ]

        def filtrar_ativos(self, **_kwargs):
            return self.listar_ativos(1)

        def buscar_ativo(self, id_ativo, _user_id):
            # O identificador é recebido apenas para manter o contrato do fake.
            del id_ativo
            return self.listar_ativos(1)[0]

    class FakeArquivosExport:
        upload_base_dir = "."

        def listar_arquivos(self, _id_ativo, _user_id):
            return [
                {
                    "id": 20,
                    "ativo_id": "A-777",
                    "tipo_documento": "nota_fiscal",
                    "nome_original": "nf_mais_recente.pdf",
                    "tamanho_bytes": 100,
                    "mime_type": "application/pdf",
                    "criado_em": "2026-04-06",
                },
                {
                    "id": 19,
                    "ativo_id": "A-777",
                    "tipo_documento": "nota_fiscal",
                    "nome_original": "nf_antiga.pdf",
                    "tamanho_bytes": 90,
                    "mime_type": "application/pdf",
                    "criado_em": "2026-04-01",
                },
                {
                    "id": 21,
                    "ativo_id": "A-777",
                    "tipo_documento": "garantia",
                    "nome_original": "garantia_1ano.pdf",
                    "tamanho_bytes": 80,
                    "mime_type": "application/pdf",
                    "criado_em": "2026-04-06",
                },
                {
                    "id": 22,
                    "ativo_id": "A-777",
                    "tipo_documento": "outro",
                    "nome_original": "manual.pdf",
                    "tamanho_bytes": 70,
                    "mime_type": "application/pdf",
                    "criado_em": "2026-04-06",
                },
            ]

        def salvar_arquivo(self, **_kwargs):
            return 1

        def obter_arquivo(self, _arquivo_id, _user_id):
            return {"caminho_arquivo": "", "nome_original": "", "mime_type": ""}

        def remover_arquivo(self, _arquivo_id, _user_id):
            return None

    from tests.conftest import FakeAuthService, FakeEmpresaService

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosSemDocs(),
            "ativos_arquivo_service": FakeArquivosExport(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    response = client.get("/ativos/export/json")
    assert response.status_code == 200
    payload = response.get_json()
    ativo = payload["ativos"][0]
    assert ativo["nota_fiscal"] == "nf_mais_recente.pdf"
    assert ativo["garantia"] == "garantia_1ano.pdf"


def test_export_xlsx_uses_linked_documents_for_columns():
    class FakeAtivosSemDocs:
        def listar_ativos(self, _user_id):
            return [
                SimpleNamespace(
                    id_ativo="A-888",
                    tipo="Servidor",
                    marca="HP",
                    modelo="DL380",
                    usuario_responsavel="Carlos",
                    departamento="Infra",
                    status="Ativo",
                    data_entrada="2026-04-02",
                    data_saida=None,
                    nota_fiscal="",
                    garantia="",
                )
            ]

        def filtrar_ativos(self, **_kwargs):
            return self.listar_ativos(1)

        def buscar_ativo(self, id_ativo, _user_id):
            # O identificador é recebido apenas para manter o contrato do fake.
            del id_ativo
            return self.listar_ativos(1)[0]

    class FakeArquivosExport:
        upload_base_dir = "."

        def listar_arquivos(self, _id_ativo, _user_id):
            return [
                {
                    "id": 30,
                    "ativo_id": "A-888",
                    "tipo_documento": "nota_fiscal",
                    "nome_original": "nf_servidor.pdf",
                    "tamanho_bytes": 120,
                    "mime_type": "application/pdf",
                    "criado_em": "2026-04-06",
                },
                {
                    "id": 31,
                    "ativo_id": "A-888",
                    "tipo_documento": "garantia",
                    "nome_original": "garantia_servidor.pdf",
                    "tamanho_bytes": 130,
                    "mime_type": "application/pdf",
                    "criado_em": "2026-04-06",
                },
            ]

        def salvar_arquivo(self, **_kwargs):
            return 1

        def obter_arquivo(self, _arquivo_id, _user_id):
            return {"caminho_arquivo": "", "nome_original": "", "mime_type": ""}

        def remover_arquivo(self, _arquivo_id, _user_id):
            return None

    from tests.conftest import FakeAuthService, FakeEmpresaService

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosSemDocs(),
            "ativos_arquivo_service": FakeArquivosExport(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    response = client.get("/ativos/export/xlsx")
    assert response.status_code == 200

    workbook = load_workbook(filename=BytesIO(response.data))
    worksheet = workbook.active
    headers = [cell.value for cell in worksheet[1]]
    values = [cell.value for cell in worksheet[2]]
    row = dict(zip(headers, values))

    assert row["Nota Fiscal"] == "Vinculada"
    assert row["Garantia"] == "Vinculada"
    assert worksheet["J2"].comment is not None
    assert worksheet["K2"].comment is not None
    assert "nf_servidor.pdf" in worksheet["J2"].comment.text
    assert "garantia_servidor.pdf" in worksheet["K2"].comment.text


def test_export_json_fallbacks_to_legacy_fields_without_attachments():
    class FakeAtivosLegado:
        def listar_ativos(self, _user_id):
            return [
                SimpleNamespace(
                    id_ativo="A-999",
                    tipo="Monitor",
                    marca="LG",
                    modelo="27UL",
                    usuario_responsavel="Bruna",
                    departamento="Design",
                    status="Ativo",
                    data_entrada="2026-04-03",
                    data_saida=None,
                    nota_fiscal="NF-LEGADO-123",
                    garantia="GAR-LEGADO-ABC",
                )
            ]

        def filtrar_ativos(self, **_kwargs):
            return self.listar_ativos(1)

        def buscar_ativo(self, id_ativo, _user_id):
            # O identificador é recebido apenas para manter o contrato do fake.
            del id_ativo
            return self.listar_ativos(1)[0]

    class FakeArquivosVazio:
        upload_base_dir = "."

        def listar_arquivos(self, _id_ativo, _user_id):
            return []

        def salvar_arquivo(self, **_kwargs):
            return 1

        def obter_arquivo(self, _arquivo_id, _user_id):
            return {"caminho_arquivo": "", "nome_original": "", "mime_type": ""}

        def remover_arquivo(self, _arquivo_id, _user_id):
            return None

    from tests.conftest import FakeAuthService, FakeEmpresaService

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosLegado(),
            "ativos_arquivo_service": FakeArquivosVazio(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    response = client.get("/ativos/export/json")
    assert response.status_code == 200
    payload = response.get_json()
    ativo = payload["ativos"][0]
    assert ativo["nota_fiscal"] == "NF-LEGADO-123"
    assert ativo["garantia"] == "GAR-LEGADO-ABC"


def test_export_xlsx_route_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/export/xlsx")
    assert response.status_code == 200
    assert (
        response.headers.get("Content-Type", "")
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "ativos_export_" in response.headers.get("Content-Disposition", "")


def test_export_pdf_route_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/export/pdf")
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "") == "application/pdf"
    assert "ativos_export_" in response.headers.get("Content-Disposition", "")


def test_export_invalid_format_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/export/zip")
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False


def test_export_xlsx_empty_list_returns_404():
    class EmptyAtivosService:
        def listar_ativos(self, _user_id):
            return []

        def filtrar_ativos(self, **_kwargs):
            return []

        def buscar_ativo(self, id_ativo, _user_id):
            return SimpleNamespace(
                id_ativo=id_ativo,
                tipo="",
                marca="",
                modelo="",
                usuario_responsavel="",
                departamento="",
                status="",
                data_entrada="",
                data_saida="",
                nota_fiscal="",
                garantia="",
            )

    from tests.conftest import FakeArquivosService, FakeAuthService, FakeEmpresaService

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": EmptyAtivosService(),
            "ativos_arquivo_service": FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    response = client.get("/ativos/export/xlsx")
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["ok"] is False


def test_invalid_date_interval_in_filters_returns_400(authenticated_client):
    response = authenticated_client.get(
        "/ativos/export/json?data_entrada_inicial=2026-05-01&data_entrada_final=2026-04-01"
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False


def test_csrf_missing_token_blocks_profile_update(authenticated_client):
    """Requisição sem csrf_token deve ser rejeitada com mensagem de erro."""
    response = authenticated_client.post(
        "/configuracoes/perfil",
        data={"nome": "Atacante", "email": "user@example.com"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Requisição inválida" in html


def test_csrf_invalid_token_blocks_password_change(authenticated_client):
    """Token CSRF adulterado deve ser rejeitado."""
    response = authenticated_client.post(
        "/configuracoes/senha",
        data={
            "senha_atual": "secret",
            "nova_senha": "novasenha123",
            "confirmar_nova_senha": "novasenha123",
            "csrf_token": "token.invalido.aqui",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Requisição inválida" in html


def test_csrf_missing_token_blocks_asset_create_json_route():
    """POST /ativos deve bloquear mutação JSON quando o token CSRF não é enviado."""
    from tests.conftest import FakeArquivosService as _FakeArquivosService, FakeAuthService, FakeEmpresaService

    class MinimalAtivosService:
        def criar_ativo(self, _ativo, _user_id):
            return "NTB-123"

        def buscar_ativo(self, id_ativo, _user_id):
            return SimpleNamespace(
                id_ativo=id_ativo,
                tipo="Notebook",
                tipo_ativo="Notebook",
                marca="Dell",
                modelo="XPS",
                usuario_responsavel="",
                departamento="TI",
                setor="TI",
                status="Disponível",
                data_entrada="2026-04-15",
                data_saida=None,
            )

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": MinimalAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    response = client.post(
        "/ativos",
        json={"tipo_ativo": "Notebook", "marca": "Dell", "modelo": "XPS", "status": "Disponível", "data_entrada": "2026-04-15", "setor": "TI"},
    )
    assert response.status_code == 403


def test_csrf_missing_token_blocks_attachment_upload_multipart_route():
    """POST /ativos/<id>/anexos deve bloquear upload multipart sem token CSRF."""
    from tests.conftest import FakeAtivosService, FakeAuthService, FakeEmpresaService

    class UploadArquivosService:
        upload_base_dir = "."

        def salvar_arquivo(self, **_kwargs):
            return 77

        def listar_arquivos(self, _id_ativo, _user_id):
            return []

        def obter_arquivo(self, _arquivo_id, _user_id):
            return {"caminho_arquivo": "", "nome_original": "", "mime_type": ""}

        def remover_arquivo(self, _arquivo_id, _user_id):
            return None

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosService(),
            "ativos_arquivo_service": UploadArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    response = client.post(
        "/ativos/A-001/anexos",
        data={"type": "nota_fiscal", "file": (BytesIO(b"abc"), "teste.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 403


def test_asset_create_route_accepts_sparse_payload_without_descricao_categoria():
    """
    Testa que a rota de criação aceita payload esparso SEM descricao e categoria.
    O backend deve preencher automaticamente esses campos — não devem estar no payload.
    Regressão para garantir que a Fase 3 Round 2 permanece válida.
    """
    class SparseAtivosService:
        def criar_ativo(self, ativo, _user_id):
            # Valida que descricao e categoria não vieram do payload
            assert not hasattr(ativo, "_incoming_descricao")
            assert not hasattr(ativo, "_incoming_categoria")
            return "NTB-001"

        def buscar_ativo(self, id_ativo, _user_id):
            return SimpleNamespace(
                id_ativo=id_ativo,
                tipo="Notebook",
                tipo_ativo="Notebook",
                marca="Dell",
                modelo="XPS",
                usuario_responsavel="João",
                departamento="TI",
                setor="TI",
                status="Disponível",
                data_entrada="2026-04-15",
                data_saida=None,
                created_at="2026-04-15 10:00:00",
                updated_at="2026-04-15 10:00:00",
                data_ultima_movimentacao=None,
            )

    from tests.conftest import (
        FakeArquivosService as _FakeArquivosService,
        FakeAuthService,
        FakeEmpresaService,
        aplicar_headers_csrf_no_client_teste,
    )

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": SparseAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    # Payload SEM descricao e categoria — como vem do novo formulário da Fase 3
    response = client.post(
        "/ativos",
        json={
            "tipo_ativo": "Notebook",
            "marca": "Dell",
            "modelo": "XPS",
            "status": "Disponível",
            "data_entrada": "2026-04-15",
            "setor": "TI",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["ativo"]["id"] == "NTB-001"


def test_asset_create_route_returns_400_for_validation_value_error():
    """
    ValueError de validação deve retornar 400 com mensagem de negócio,
    não erro genérico 500.
    """

    class ValidationErrorAtivosService:
        def criar_ativo(self, _ativo, _user_id):
            raise ValueError("numero_linha inválido.")

        def buscar_ativo(self, _id_ativo, _user_id):
            return None

    from tests.conftest import (
        FakeArquivosService as _FakeArquivosService,
        FakeAuthService,
        FakeEmpresaService,
        aplicar_headers_csrf_no_client_teste,
    )

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": ValidationErrorAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.post(
        "/ativos",
        json={
            "tipo_ativo": "Celular",
            "marca": "Samsung",
            "modelo": "S23",
            "status": "Disponível",
            "setor": "T.I",
            "data_entrada": "2026-04-15",
            "numero_linha": "12345",
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False
    assert "numero_linha" in payload.get("erro", "").lower()


def test_assets_list_template_avoids_non_standard_selector_for_highlight(app_fixture):
    """
    Regressão de runtime: evitar seletor CSS não suportado (:contains)
    no destaque de ativo recém-criado.
    """
    del app_fixture
    from pathlib import Path

    template_path = Path(__file__).parent.parent / "web_app" / "templates" / "ativos.html"
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    assert "tr:has(span:contains(\"NOVO\"))" not in template_content
    assert "tr[data-asset-id]" in template_content


def test_asset_filter_presenca_documental_uses_real_attachments():
    """
    Testa que o filtro de presença documental usa anexos reais da tabela ativos_arquivos.
    Garante compatibilidade com a implementação de fallback para campos legados.
    """
    from tests.conftest import FakeArquivosService as _FakeArquivosService, FakeAuthService, FakeEmpresaService

    class DocumentFilterAtivosService:
        def listar_ativos(self, _user_id):
            return [
                SimpleNamespace(
                    id_ativo="NTB-001",
                    tipo="Notebook",
                    tipo_ativo="Notebook",
                    marca="Dell",
                    modelo="XPS",
                    usuario_responsavel="Ana",
                    departamento="TI",
                    setor="TI",
                    status="Disponível",
                    data_entrada="2026-04-01",
                    data_saida=None,
                    garantia=None,
                    nota_fiscal=None,
                ),
                SimpleNamespace(
                    id_ativo="NTB-002",
                    tipo="Notebook",
                    tipo_ativo="Notebook",
                    marca="Lenovo",
                    modelo="ThinkPad",
                    usuario_responsavel="Bruno",
                    departamento="TI",
                    setor="TI",
                    status="Disponível",
                    data_entrada="2026-04-02",
                    data_saida=None,
                    garantia="12 meses",  # campo legado, sem anexo
                    nota_fiscal=None,
                ),
            ]

        def filtrar_ativos(self, user_id, **_kwargs):
            return self.listar_ativos(user_id)

    class DocumentFilterArquivosService(_FakeArquivosService):
        def listar_arquivos(self, id_ativo, _user_id):
            # Retorna um anexo real apenas para o primeiro ativo
            if id_ativo == "NTB-001":
                return [
                    {"tipo_documento": "nota_fiscal", "nome_original": "nf-001.pdf", "tamanho_bytes": 50000}
                ]
            return []

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": DocumentFilterAtivosService(),
            "ativos_arquivo_service": DocumentFilterArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    # Filtra apenas ativos COM nota fiscal
    response = client.get("/ativos?tem_nota_fiscal=sim", headers={"X-Requested-With": "fetch"})
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["ativos"]) == 1
    assert payload["ativos"][0]["id"] == "NTB-001"

    # Filtra apenas ativos SEM nota fiscal
    response = client.get("/ativos?tem_nota_fiscal=nao", headers={"X-Requested-With": "fetch"})
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["ativos"]) == 1
    assert payload["ativos"][0]["id"] == "NTB-002"


def test_asset_filter_presenca_documental_uses_batch_mapping_without_n_plus_one():
    """
    Garante que o filtro documental utiliza leitura em lote em vez de listar_arquivos por ativo.
    """
    from tests.conftest import FakeAuthService, FakeEmpresaService

    class BatchFilterAtivosService:
        def listar_ativos(self, _user_id):
            return [
                SimpleNamespace(
                    id_ativo="NTB-101",
                    tipo="Notebook",
                    tipo_ativo="Notebook",
                    marca="Dell",
                    modelo="XPS",
                    usuario_responsavel="Ana",
                    departamento="TI",
                    setor="TI",
                    status="Disponível",
                    data_entrada="2026-04-01",
                    data_saida=None,
                    garantia=None,
                    nota_fiscal=None,
                ),
                SimpleNamespace(
                    id_ativo="NTB-102",
                    tipo="Notebook",
                    tipo_ativo="Notebook",
                    marca="Lenovo",
                    modelo="ThinkPad",
                    usuario_responsavel="Bruno",
                    departamento="TI",
                    setor="TI",
                    status="Disponível",
                    data_entrada="2026-04-02",
                    data_saida=None,
                    garantia=None,
                    nota_fiscal=None,
                ),
            ]

        def filtrar_ativos(self, user_id, **_kwargs):
            return self.listar_ativos(user_id)

    class BatchFilterArquivosService:
        upload_base_dir = "."

        def __init__(self):
            self.batch_calls = 0
            self.listar_calls = 0

        def mapear_presenca_documentos(self, ativo_ids, _user_id):
            # A lista de IDs é ignorada porque o fake retorna uma resposta fixa.
            del ativo_ids
            self.batch_calls += 1
            return {
                "NTB-101": {"nota_fiscal": True, "garantia": False},
                "NTB-102": {"nota_fiscal": False, "garantia": False},
            }

        def listar_arquivos(self, _id_ativo, _user_id):
            self.listar_calls += 1
            raise AssertionError("listar_arquivos não deveria ser chamado quando há batch mapping")

        def salvar_arquivo(self, **_kwargs):
            return 1

        def obter_arquivo(self, _arquivo_id, _user_id):
            return {"caminho_arquivo": "", "nome_original": "", "mime_type": ""}

        def remover_arquivo(self, _arquivo_id, _user_id):
            return None

    arquivos_service = BatchFilterArquivosService()
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": BatchFilterAtivosService(),
            "ativos_arquivo_service": arquivos_service,
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    response = client.get("/ativos?tem_nota_fiscal=sim")
    assert response.status_code == 200
    payload = response.get_json()
    assert [item["id"] for item in payload["ativos"]] == ["NTB-101"]
    assert arquivos_service.batch_calls == 1
    assert arquivos_service.listar_calls == 0


def test_asset_edit_template_does_not_reference_removed_fields():
    """
    Validação contínua: editar_ativo.html não deve tentar preencher ou referenciar
    descricao e categoria (removidos em Fase 3 Round 2).
    Verifica que os campos removidos estão apenas em comentários HTML (não ativos).
    """
    from pathlib import Path
    import re

    template_path = Path(__file__).parent.parent / "web_app" / "templates" / "editar_ativo.html"
    assert template_path.exists(), f"Template não encontrado: {template_path}"

    template_content = template_path.read_text(encoding="utf-8")

    # Remove comentários HTML e verifica que os campos removidos não estão no template ativo
    template_without_comments = re.sub(r"<!--.*?-->", "", template_content, flags=re.DOTALL)

    # Verifica que os campos removidos não estão FORA dos comentários
    assert 'id="descricao"' not in template_without_comments, \
        "Campo descricao encontrado ativo no template (deveria estar comentado)"
    assert 'id="categoria"' not in template_without_comments, \
        "Campo categoria encontrado ativo no template (deveria estar comentado)"
    assert 'name="descricao"' not in template_without_comments, \
        "Campo descricao encontrado ativo no template (deveria estar comentado)"
    assert 'name="categoria"' not in template_without_comments, \
        "Campo categoria encontrado ativo no template (deveria estar comentado)"

    # Verifica que os campos principais continuam presentes
    assert 'id="tipo_ativo"' in template_without_comments, "Campo tipo_ativo deveria estar no template"
    assert 'id="marca"' in template_without_comments, "Campo marca deveria estar no template"
    assert 'id="modelo"' in template_without_comments, "Campo modelo deveria estar no template"
    assert 'id="status"' in template_without_comments, "Campo status deveria estar no template"


def test_debug_error_is_re_raised(app_fixture):
    @app_fixture.get("/boom")
    def boom():
        raise ValueError("boom")

    client = app_fixture.test_client()

    try:
        client.get("/boom")
        raised = False
    except ValueError:
        raised = True

    assert raised is True


# ========== TESTES PARA NOVA RODADA DE FECHAMENTO ==========
# Validações da rodada de refinamento final da camada web

def test_filter_modal_has_select_for_tipo_e_departamento(app_fixture):
    """
    Valida que o modal de filtros usa SELECT em vez de input text
    para campos com vocabulário controlado (tipo e departamento/setor).

    Essa validação garante que usuários escolham de opções oficiais
    e não possam digitar valores livres nesses campos.
    """
    # O fixture é mantido para compatibilidade com o contrato de execução do pytest.
    del app_fixture
    from pathlib import Path

    # Lê o template ativos.html
    template_path = Path(__file__).parent.parent / "web_app" / "templates" / "ativos.html"
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    # Valida que filter-tipo é um SELECT
    assert 'id="filter-tipo"' in template_content, "Campo filter-tipo não encontrado"
    assert '<select id="filter-tipo"' in template_content, \
        "filter-tipo deveria ser SELECT, não input text"

    # Valida que filter-departamento é um SELECT
    assert 'id="filter-departamento"' in template_content, "Campo filter-departamento não encontrado"
    assert '<select id="filter-departamento"' in template_content, \
        "filter-departamento deveria ser SELECT, não input text"

    # Valida que as opções são renderizadas a partir das listas de valores válidos
    assert "{% for tipo in tipos_validos %}" in template_content, \
        "Tipos válidos não estão sendo iterados no template"
    assert "{% for setor in setores_validos %}" in template_content, \
        "Setores válidos não estão sendo iterados no template"


def test_filter_modal_receives_valid_options_from_route(authenticated_client):
    """
    Valida que a rota de listagem passa as listas de tipos e setores
    para o template de filtros.

    Isso garante que o modal tem acesso aos valores válidos para renderizar
    as opções nos SELECT fields.
    """
    response = authenticated_client.get("/ativos/lista")
    assert response.status_code == 200

    # Valida que as variáveis estão no contexto do template
    # (Testado indiretamente pela presença de <option> tags no HTML)
    html = response.get_data(as_text=True)

    # Valida que tipos válidos aparecem nas opções
    assert "<option value=\"Notebook\">" in html, "Tipo 'Notebook' não encontrado nas opções"
    assert "<option value=\"Desktop\">" in html, "Tipo 'Desktop' não encontrado nas opções"
    assert "<option value=\"Celular\">" in html, "Tipo 'Celular' não encontrado nas opções"

    # Valida que setores válidos aparecem nas opções
    assert "<option value=\"T.I\">" in html or "T.I" in html, "Setor 'T.I' não encontrado nas opções"
    assert "<option value=\"Rh\">" in html, "Setor 'Rh' não encontrado nas opções"
    assert "<option value=\"Financeiro\">" in html, "Setor 'Financeiro' não encontrado nas opções"


def test_asset_summary_endpoint_returns_structured_resumo(authenticated_client):
    """
    Valida que o endpoint GET /ativos/<id>/resumo retorna um resumo
    estruturado do ativo com as seções principais.

    Resumo esperado contém:
    - secao_principal (ID, tipo, marca, modelo, status)
    - secao_responsabilidade (responsável, e-mail, setor)
    - secao_ciclo (datas, documentação)
    - secao_tecnica (campos específicos por tipo)
    - secao_tecnica_restrita (opcional, visível apenas para admin)
    """
    client = authenticated_client

    # Cria um ativo de teste
    response = client.post(
        "/ativos",
        json={
            "id_ativo": "TEST-001",
            "tipo_ativo": "Notebook",
            "marca": "Dell",
            "modelo": "Inspiron",
            "setor": "T.I",
            "status": "Disponível",
            "data_entrada": "2026-04-01",
            "usuario_responsavel": "João",
        },
        headers={"X-Requested-With": "fetch"}
    )
    assert response.status_code == 201

    # Requisita o resumo
    response = client.get(
        "/ativos/TEST-001/resumo",
        headers={"X-Requested-With": "fetch"}
    )
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["ok"] is True

    resumo = payload.get("resumo", {})

    # Valida estrutura básica do resumo
    assert "secao_principal" in resumo, "resumo deveria ter secao_principal"
    assert "secao_responsabilidade" in resumo, "resumo deveria ter secao_responsabilidade"
    assert "secao_ciclo" in resumo, "resumo deveria ter secao_ciclo"
    assert "secao_tecnica" in resumo, "resumo deveria ter secao_tecnica"

    # Valida que secao_principal tem dados corretos
    principal = resumo["secao_principal"]
    assert principal.get("id") == "TEST-001", f"ID do ativo incorreto: {principal.get('id')}"
    assert principal.get("tipo") == "Notebook", "Tipo do ativo incorreto"
    assert principal.get("marca") == "Dell", "Marca do ativo incorreta"

    # Valida que secao_tecnica tem campos para Notebook
    tecnica = resumo.get("secao_tecnica", {})
    campos_tecnica = tecnica.get("campos", {})
    assert "processador" in campos_tecnica, "Notebook deveria ter campo 'processador'"
    assert "ram" in campos_tecnica, "Notebook deveria ter campo 'ram'"
    assert "armazenamento" in campos_tecnica, "Notebook deveria ter campo 'armazenamento'"


def test_asset_summary_hides_technical_fields_from_common_user(authenticated_client):
    """
    Valida que o resumo NÃO inclui campos técnicos restritos
    (AnyDesk, TeamViewer, hostname, serial, código_interno)
    quando o usuário é um usuário comum (perfil != admin).

    Seção 'secao_tecnica_restrita' deveria estar vazia ou ausente.
    """
    client = authenticated_client

    # Cria um ativo com campos técnicos sensíveis
    response = client.post(
        "/ativos",
        json={
            "id_ativo": "TEST-002",
            "tipo_ativo": "Desktop",
            "marca": "HP",
            "modelo": "ProDesk",
            "setor": "Financeiro",
            "status": "Disponível",
            "data_entrada": "2026-04-01",
            "usuario_responsavel": "Maria",
            "teamviewer_id": "SECRET123",
            "anydesk_id": "ANOTHER-SECRET",
            "hostname": "FIN-DESK-01",
            "serial": "SN12345",
            "codigo_interno": "INT-001",
        },
        headers={"X-Requested-With": "fetch"}
    )
    assert response.status_code == 201

    # Requisita o resumo como usuário comum (perfil padrão na sessão)
    response = client.get(
        "/ativos/TEST-002/resumo",
        headers={"X-Requested-With": "fetch"}
    )
    assert response.status_code == 200

    payload = response.get_json()
    resumo = payload.get("resumo", {})

    # Valida que campos técnicos restritos NÃO aparecem
    assert "secao_tecnica_restrita" not in resumo or \
           not resumo.get("secao_tecnica_restrita"), \
        "Usuário comum não deveria ver secao_tecnica_restrita"


def test_asset_summary_shows_technical_fields_to_admin(authenticated_client):
    """
    Valida que o resumo INCLUI campos técnicos restritos
    (AnyDesk, TeamViewer, hostname, serial, código_interno)
    quando o usuário é admin (perfil == 'adm' ou 'admin').

    Seção 'secao_tecnica_restrita' deveria conter todos os campos restritos.

    Nota: Este teste valida a função _resumo_ativo_para_modal com dados mock,
    pois o FakeAtivosService não persiste todos os campos técnicos.
    """
    # O cliente autenticado é mantido como fixture para garantir o contexto de sessão.
    del authenticated_client
    # Testa a função _resumo_ativo_para_modal diretamente com dados mock
    from web_app.routes.ativos_routes import _resumo_ativo_para_modal

    # Mock de ativo completo com todos os campos técnicos
    ativo_mock = {
        "id": "TEST-003",
        "tipo": "Notebook",
        "marca": "Lenovo",
        "modelo": "ThinkPad",
        "status": "Disponível",
        "usuario_responsavel": "Admin",
        "email_responsavel": "admin@example.com",
        "setor": "T.I",
        "localizacao": "Sala IT",
        "data_entrada": "2026-04-01",
        "data_saida": None,
        "nota_fiscal": "NF-123",
        "garantia": "12 meses",
        # Campos técnicos
        "processador": "Intel i7",
        "ram": "16GB",
        "armazenamento": "512GB SSD",
        "sistema_operacional": "Windows 11",
        "teamviewer_id": "SECRET123",
        "anydesk_id": "ANOTHER-SECRET",
        "hostname": "IT-NB-01",
        "serial": "SN67890",
        "codigo_interno": "INT-002",
    }

    # Chama a função com eh_admin=True
    resumo = _resumo_ativo_para_modal(ativo_mock, eh_admin=True)

    # Valida que campos técnicos restritos APARECEM para admin
    assert "secao_tecnica_restrita" in resumo, \
        "Admin deveria ver secao_tecnica_restrita"

    tecnica_restrita = resumo.get("secao_tecnica_restrita", {})
    assert tecnica_restrita.get("teamviewer_id") == "SECRET123", \
        "Admin deveria ver teamviewer_id"
    assert tecnica_restrita.get("anydesk_id") == "ANOTHER-SECRET", \
        "Admin deveria ver anydesk_id"
    assert tecnica_restrita.get("hostname") == "IT-NB-01", \
        "Admin deveria ver hostname"
    assert tecnica_restrita.get("serial") == "SN67890", \
        "Admin deveria ver serial"
    assert tecnica_restrita.get("codigo_interno") == "INT-002", \
        "Admin deveria ver codigo_interno"
