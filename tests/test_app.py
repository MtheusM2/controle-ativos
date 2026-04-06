from __future__ import annotations

from types import SimpleNamespace

from web_app.app import create_app

def test_healthcheck(http_client):
    response = http_client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"ok": True, "status": "healthy"}


def test_dashboard_authenticated(authenticated_client):
    response = authenticated_client.get("/dashboard")
    assert response.status_code == 200
    assert "Dashboard de Ativos" in response.get_data(as_text=True)


def test_assets_listing_page_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/lista")
    assert response.status_code == 200
    assert "Listagem de Ativos" in response.get_data(as_text=True)


def test_asset_create_page_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/novo")
    assert response.status_code == 200
    assert "Cadastro de ativo" in response.get_data(as_text=True)


def test_asset_edit_page_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/editar/A-001")
    assert response.status_code == 200
    assert "Edição do ativo" in response.get_data(as_text=True)


def test_asset_view_page_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/visualizar/A-001", follow_redirects=True)
    assert response.status_code == 200
    assert "Especificacoes do ativo" in response.get_data(as_text=True)


def test_asset_details_page_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/detalhes/A-001")
    assert response.status_code == 200
    assert "Documentos vinculados" in response.get_data(as_text=True)


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


def test_ativos_route_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["ativos"]


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

    from io import BytesIO
    from tests.conftest import FakeAtivosService, FakeAuthService, FakeEmpresaService

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


def test_export_json_route_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/export/json")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["formato"] == "json"
    assert isinstance(payload["ativos"], list)


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