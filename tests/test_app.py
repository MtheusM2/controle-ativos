from __future__ import annotations

from io import BytesIO
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


def test_asset_edit_page_contains_movement_modal_flow_elements(authenticated_client):
    response = authenticated_client.get("/ativos/editar/A-001")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # Garante que a UI da Fase 3 está presente no template de edição.
    assert "movement-confirmation-modal" in html
    assert "Confirmar e salvar" in html
    assert "/movimentacao/preview" in html
    assert "/movimentacao/confirmar" in html


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

    from tests.conftest import FakeArquivosService as _FakeArquivosService, FakeAuthService, FakeEmpresaService

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

    from tests.conftest import FakeArquivosService as _FakeArquivosService, FakeAuthService, FakeEmpresaService

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

    from tests.conftest import FakeArquivosService as _FakeArquivosService, FakeAuthService, FakeEmpresaService

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

    from tests.conftest import FakeArquivosService as _FakeArquivosService, FakeAuthService, FakeEmpresaService

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

    from tests.conftest import FakeArquivosService as _FakeArquivosService, FakeAuthService, FakeEmpresaService

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
    assert "<option value=\"RH\">" in html, "Setor 'RH' não encontrado nas opções"
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