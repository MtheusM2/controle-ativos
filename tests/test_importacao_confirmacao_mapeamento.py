from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from itsdangerous import URLSafeTimedSerializer

from services.auditoria_importacao_service import AuditoriaImportacaoService
from services.ativos_service import AtivosService
from web_app.app import create_app


CSV_CONFIRMACAO_REAL = (
    "tipo_ativo,marca,modelo,usuario_responsavel,setor,status,data_entrada,nota_fiscal\n"
    "Monitor,Samsung,24POLEGADAS,Matheus,Rh,Em Uso,2026-04-06,NF-001\n"
).encode("utf-8")

CSV_COM_AVISOS = (
    "tipo_ativo,marca,modelo,usuario_responsavel,setor,status,data_entrada\n"
    "Notebook,Dell,Latitude,Fulano Fantasma,T.I,Disponivel,2026-04-10\n"
).encode("utf-8")


class _FakeAuthServiceAdmin:
    def autenticar(self, *_args, **_kwargs):
        return SimpleNamespace(
            id=1,
            nome="Admin Demo",
            email="admin@example.com",
            perfil="admin",
            empresa_id=10,
            empresa_nome="Empresa Demo",
            lembrar_me_ativo=False,
        )

    def registrar_usuario(self, **_kwargs):
        return 1

    def obter_usuario_por_id(self, _user_id: int):
        return {
            "id": 1,
            "nome": "Admin Demo",
            "email": "admin@example.com",
            "perfil": "admin",
            "empresa_id": 10,
            "empresa_nome": "Empresa Demo",
            "lembrar_me_ativo": False,
            "suporta_nome": True,
            "suporta_lembrar_me": True,
        }

    def atualizar_preferencia_lembrar_me(self, *_args, **_kwargs):
        return None

    def atualizar_proprio_perfil(self, *_args, **_kwargs):
        return self.obter_usuario_por_id(1)

    def alterar_senha_propria(self, *_args, **_kwargs):
        return None

    def obter_pergunta_recuperacao(self, _email: str):
        return "Pergunta de seguranca?"

    def redefinir_senha(self, **_kwargs):
        return None


class _FakeEmpresaService:
    def listar_empresas_ativas(self):
        return [SimpleNamespace(id=10, nome="Empresa Demo")]


class _DummyArquivosService:
    upload_base_dir = "."


def _gerar_token_csrf(app, user_id: int) -> str:
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="csrf")
    return serializer.dumps(f"user:{user_id}")


def _stub_auditoria(monkeypatch, *, usuarios_validos: set[str] | None = None) -> None:
    monkeypatch.setattr(
        AuditoriaImportacaoService,
        "iniciar_auditoria",
        staticmethod(lambda **kwargs: "IMP-TEST-CONFIRM"),
    )
    monkeypatch.setattr(
        AuditoriaImportacaoService,
        "obter_usuarios_validos",
        staticmethod(lambda empresa_id: usuarios_validos or {"Matheus", "Ana Silva"}),
    )
    monkeypatch.setattr(
        AuditoriaImportacaoService,
        "detectar_duplicatas",
        staticmethod(lambda ids_csv, empresa_id: {}),
    )
    monkeypatch.setattr(
        AuditoriaImportacaoService,
        "detectar_seriais_duplicados",
        staticmethod(lambda seriais_csv, empresa_id: {}),
    )
    monkeypatch.setattr(
        AuditoriaImportacaoService,
        "registrar_preview_gerado",
        staticmethod(lambda **kwargs: None),
    )
    monkeypatch.setattr(
        AuditoriaImportacaoService,
        "registrar_confirmacao",
        staticmethod(lambda **kwargs: None),
    )
    monkeypatch.setattr(
        AuditoriaImportacaoService,
        "registrar_resultado_importacao",
        staticmethod(lambda **kwargs: None),
    )


def _criar_client(monkeypatch):
    service = AtivosService()
    ids_criados: list[str] = []

    monkeypatch.setattr(
        service,
        "_obter_contexto_acesso",
        lambda user_id: {"id": user_id, "perfil": "admin", "empresa_id": 10, "empresa_nome": "Empresa Demo"},
    )
    monkeypatch.setattr(service, "_usuario_eh_admin", lambda contexto: True)

    def _criar_ativo_fake(ativo, _user_id):
        novo_id = f"OPU-{len(ids_criados) + 1:06d}"
        ids_criados.append(novo_id)
        return novo_id

    monkeypatch.setattr(service, "criar_ativo", _criar_ativo_fake)

    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": _FakeAuthServiceAdmin(),
            "empresa_service": _FakeEmpresaService(),
            "ativos_service": service,
            "ativos_arquivo_service": _DummyArquivosService(),
        },
    )

    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "admin@example.com"
        session_data["user_perfil"] = "admin"
        session_data["user_empresa_id"] = 10
        session_data["user_empresa_nome"] = "Empresa Demo"

    client.environ_base["HTTP_X_CSRF_TOKEN"] = _gerar_token_csrf(app, user_id=1)
    client.environ_base["HTTP_X_REQUESTED_WITH"] = "fetch"
    return app, client, ids_criados


def _extrair_mapeamento_frontend(preview: dict) -> dict[str, str | None]:
    mapeamento = {}
    for grupo in ("exatas", "sugeridas", "ignoradas"):
        for coluna in preview.get("colunas", {}).get(grupo, []):
            mapeamento[coluna["coluna_origem"]] = coluna.get("campo_destino")
    return mapeamento


def test_confirmacao_rota_real_reutiliza_mapeamento_do_preview(monkeypatch):
    _stub_auditoria(monkeypatch)
    _app, client, ids_criados = _criar_client(monkeypatch)

    preview_response = client.post(
        "/ativos/importar/preview",
        data={"file": (BytesIO(CSV_CONFIRMACAO_REAL), "ativos_export_20260428_114556.csv")},
        content_type="multipart/form-data",
    )

    assert preview_response.status_code == 200
    preview_payload = preview_response.get_json()
    preview = preview_payload["preview"]

    mapeamento_frontend = _extrair_mapeamento_frontend(preview)
    destinos = {valor for valor in mapeamento_frontend.values() if valor}

    assert "tipo_ativo" in destinos
    assert "data_entrada" in destinos

    response = client.post(
        "/ativos/importar/confirmar",
        data={
            "file": (BytesIO(CSV_CONFIRMACAO_REAL), "ativos_export_20260428_114556.csv"),
            "id_lote": preview_payload["id_lote"],
            "modo_importacao": "validas_e_avisos",
            "sugestoes_confirmadas": "{}",
            "mapeamento_confirmado": __import__("json").dumps(mapeamento_frontend),
            "linhas_descartadas": "[]",
            "edicoes_por_linha": "{}",
            "revisor_dados": "on",
            "confirma_duplicatas": "on",
            "aceita_avisos": "on",
            "autoriza_importacao": "on",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code in (200, 201)

    payload = response.get_json()
    resultado = payload["resultado"]

    assert payload["ok"] is True
    assert resultado["importados"] == 1
    assert resultado["falhas"] == 0
    assert not any("Campos obrigatorios nao mapeados" in erro for erro in resultado.get("erros", []))
    assert ids_criados == ["OPU-000001"]


def test_confirmacao_rota_real_importa_linha_com_aviso_em_modo_validas_e_avisos(monkeypatch):
    _stub_auditoria(monkeypatch, usuarios_validos={"Ana Silva"})
    _app, client, ids_criados = _criar_client(monkeypatch)

    preview_response = client.post(
        "/ativos/importar/preview",
        data={"file": (BytesIO(CSV_COM_AVISOS), "ativos_export_warnings.csv")},
        content_type="multipart/form-data",
    )

    assert preview_response.status_code == 200
    preview_payload = preview_response.get_json()
    preview = preview_payload["preview"]
    mapeamento_frontend = _extrair_mapeamento_frontend(preview)

    assert preview["validacao_detalhes"]["linhas_com_aviso"] > 0
    assert preview["validacao_detalhes"]["linhas_com_erro"] == 0

    response = client.post(
        "/ativos/importar/confirmar",
        data={
            "file": (BytesIO(CSV_COM_AVISOS), "ativos_export_warnings.csv"),
            "id_lote": preview_payload["id_lote"],
            "modo_importacao": "validas_e_avisos",
            "sugestoes_confirmadas": "{}",
            "mapeamento_confirmado": __import__("json").dumps(mapeamento_frontend),
            "linhas_descartadas": "[]",
            "edicoes_por_linha": "{}",
            "revisor_dados": "on",
            "confirma_duplicatas": "on",
            "aceita_avisos": "on",
            "autoriza_importacao": "on",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code in (200, 201)

    payload = response.get_json()
    resultado = payload["resultado"]

    assert payload["ok"] is True
    assert resultado["importados"] == 1
    assert resultado["falhas"] == 0
    assert resultado["avisos"]
    assert ids_criados == ["OPU-000001"]


def test_template_confirmacao_envia_json_consolidado_sem_disabled_no_mapeamento():
    template = Path("web_app/templates/importar_ativos.html").read_text(encoding="utf-8")

    assert 'formData.append("mapeamento_confirmado", JSON.stringify(construirMapeamentoConfirmado()))' in template

    bloco_select = re.search(
        r"const select = document\.createElement\('select'\);(?P<bloco>.*?)tdCampo\.appendChild\(select\);",
        template,
        flags=re.DOTALL,
    )

    assert bloco_select is not None
    assert ".disabled" not in bloco_select.group("bloco")
