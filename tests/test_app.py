from __future__ import annotations

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
    response = authenticated_client.get("/ativos/visualizar/A-001")
    assert response.status_code == 200
    assert "Visualização do ativo" in response.get_data(as_text=True)


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


def test_export_json_route_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/export/json")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["formato"] == "json"
    assert isinstance(payload["ativos"], list)


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