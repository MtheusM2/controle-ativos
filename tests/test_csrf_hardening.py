"""
Testes da rodada de hardening final - validações abrangentes de proteção CSRF.

Estes testes cobrem rejeição de requisições sem token CSRF em todos os
endpoints mutáveis críticos após a refatoração para usar decorator @require_csrf().
"""

from __future__ import annotations

from io import BytesIO
from tests.conftest import (
    FakeAtivosService,
    FakeAuthService,
    FakeEmpresaService,
    FakeArquivosService as _FakeArquivosService,
    aplicar_headers_csrf_no_client_teste,
)
from web_app.app import create_app


def test_csrf_missing_token_blocks_asset_delete():
    """
    DELETE /ativos/<id> deve rejeitar requisição sem token CSRF com status 403.

    Valida que exclusão de ativos requer token CSRF válido, mesmo quando
    as credenciais de autenticação estão presentes.
    """
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    # DELETE sem token CSRF deve ser rejeitado
    response = client.delete("/ativos/A-001")
    assert response.status_code == 403
    payload = response.get_json()
    assert payload["ok"] is False
    assert "erro" in payload


def test_csrf_missing_token_blocks_csv_import():
    """
    POST /ativos/import/csv deve rejeitar requisição sem token CSRF com status 403.

    Valida que importação em lote de ativos requer token CSRF válido para
    prevenir ataque CSRF que poderia injetar múltiplos ativos maliciosos.
    """
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    # POST /ativos/import/csv sem token CSRF deve ser rejeitado
    response = client.post(
        "/ativos/import/csv",
        data={"file": (BytesIO(b"tipo,marca,modelo\nNotebook,Dell,XPS"), "assets.csv")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 403
    payload = response.get_json()
    assert payload["ok"] is False


def test_csrf_missing_token_blocks_movement_confirmation():
    """
    POST /ativos/<id>/movimentacao/confirmar deve rejeitar requisição sem token CSRF com status 403.

    Valida que confirmação de movimentação (alteração de status/responsabilidade)
    requer token CSRF válido para prevenir mudanças não autorizadas.
    """
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    # POST /ativos/<id>/movimentacao/confirmar sem token CSRF deve ser rejeitado
    response = client.post(
        "/ativos/A-001/movimentacao/confirmar",
        json={
            "dados_formulario": {"status": "Em Uso"},
            "ajustes_movimentacao": {},
        },
    )
    assert response.status_code == 403
    payload = response.get_json()
    assert payload["ok"] is False


def test_csrf_valid_token_allows_asset_delete():
    """
    DELETE /ativos/<id> com token CSRF válido deve ser aceito e processar exclusão.

    Valida que quando o token CSRF é válido, a exclusão do ativo é permitida
    e retorna sucesso (200 ou 404 se ativo não existe, mas NÃO 403).
    """
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    # Aplica headers CSRF válidos
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    # DELETE com token CSRF válido deve processar
    response = client.delete("/ativos/A-001")
    # Pode retornar 200 (sucesso), 404 (ativo não encontrado), etc - o importante é NÃO 403
    assert response.status_code != 403
    if response.status_code in [200, 204]:
        payload = response.get_json()
        assert payload.get("ok") is True


def test_csrf_missing_token_blocks_movement_preview():
    """
    POST /ativos/<id>/movimentacao/preview deve rejeitar requisição sem token CSRF.

    Valida que a geração de prévia de movimentação também requer proteção CSRF,
    mesmo que não altere dados (é um estado transitório importante para segurança).
    """
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    # POST /ativos/<id>/movimentacao/preview sem token CSRF deve ser rejeitado
    response = client.post(
        "/ativos/A-001/movimentacao/preview",
        json={"tipo_ativo": "Notebook", "status": "Disponível"},
    )
    assert response.status_code == 403


def test_preview_without_login_returns_401_before_csrf_validation():
    """
    POST /ativos/<id>/movimentacao/preview sem sessão deve retornar 401.

    Garante o contrato de ordem de validação: autenticação vem antes do CSRF.
    """
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()

    # Sem login e sem token CSRF: prioridade deve ser 401 (não 403).
    response = client.post(
        "/ativos/A-001/movimentacao/preview",
        json={"tipo_ativo": "Notebook", "status": "Disponível"},
    )
    assert response.status_code == 401


def test_preview_with_login_and_valid_csrf_allows_success():
    """
    POST /ativos/<id>/movimentacao/preview com sessão e CSRF válido deve ter sucesso.

    Completa o contrato: login + CSRF válido não deve ser bloqueado por 401/403.
    """
    class PreviewAtivosService(FakeAtivosService):
        """
        Double focado no cenário de sucesso da prévia de movimentação.
        """

        def gerar_preview_atualizacao(self, id_ativo, dados, user_id):
            # Mantém contrato mínimo esperado pela rota para retornar 200.
            return {"id_ativo": id_ativo, "dados": dados, "user_id": user_id}

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": PreviewAtivosService(),
            "ativos_arquivo_service": _FakeArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"

    # Com sessão válida, aplica token CSRF para atravessar a segunda barreira de segurança.
    aplicar_headers_csrf_no_client_teste(client, app, user_id=1)

    response = client.post(
        "/ativos/A-001/movimentacao/preview",
        json={"tipo_ativo": "Notebook", "status": "Disponível"},
    )
    assert response.status_code == 200
