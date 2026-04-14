from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from openpyxl import load_workbook
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


def test_asset_create_page_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/novo")
    assert response.status_code == 200
    assert "Cadastro de ativo" in response.get_data(as_text=True)


def test_asset_create_page_uses_safe_attachment_int_route_builder(authenticated_client):
    response = authenticated_client.get("/ativos/novo")
    html = response.get_data(as_text=True)
    assert "templateUrl.replace(/\\/0(?=\\/|$)/" in html


def test_asset_edit_page_authenticated(authenticated_client):
    response = authenticated_client.get("/ativos/editar/A-001")
    assert response.status_code == 200
    assert "Edição do ativo" in response.get_data(as_text=True)


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

    from tests.conftest import FakeArquivosService as _FakeArquivosService, FakeAuthService, FakeEmpresaService

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

    from tests.conftest import FakeArquivosService as _FakeArquivosService, FakeAuthService, FakeEmpresaService

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

    from tests.conftest import FakeAtivosService, FakeAuthService, FakeEmpresaService

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

    from tests.conftest import FakeAtivosService, FakeAuthService, FakeEmpresaService

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

    response = client.delete("/anexos/7")
    assert response.status_code == 200
    assert fake_arquivos.removed_ids == [7]


def test_service_delete_keeps_db_cleanup_when_physical_file_is_missing(tmp_path):
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