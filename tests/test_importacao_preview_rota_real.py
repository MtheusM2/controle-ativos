from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

from itsdangerous import URLSafeTimedSerializer

from services.auditoria_importacao_service import AuditoriaImportacaoService
from services.importacao_service_seguranca import ServicoImportacaoComSeguranca
from web_app.app import create_app


CSV_EXPORTADO_SISTEMA = (
    "tipo_ativo,marca,modelo,setor,status,data_entrada,usuario_responsavel,email_responsavel\n"
    "Notebook,Dell,Latitude 5530,T.I,Disponível,2026-01-15,Ana Silva,ana@example.com\n"
    "Monitor,LG,UltraWide,Rh,Em Uso,2026-01-16,Bruno Lima,bruno@example.com\n"
    "Celular,Samsung,Galaxy S24,Marketing,Reservado,2026-01-17,Caio Souza,caio@example.com\n"
).encode("utf-8")


class _FakeAuthService:
    def autenticar(self, *_args, **_kwargs):
        return SimpleNamespace(
            id=1,
            nome="Usuario Demo",
            email="user@example.com",
            perfil="usuario",
            empresa_id=10,
            empresa_nome="Empresa Demo",
            lembrar_me_ativo=False,
        )

    def registrar_usuario(self, **_kwargs):
        return 1

    def obter_usuario_por_id(self, _user_id: int):
        return {
            "id": 1,
            "nome": "Usuario Demo",
            "email": "user@example.com",
            "perfil": "usuario",
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


class _DummyAtivosService:
    pass


class _DummyArquivosService:
    upload_base_dir = "."


def _gerar_token_csrf(app, user_id: int) -> str:
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="csrf")
    return serializer.dumps(f"user:{user_id}")


def _stub_auditoria(monkeypatch) -> None:
    monkeypatch.setattr(
        AuditoriaImportacaoService,
        "iniciar_auditoria",
        staticmethod(lambda **kwargs: "IMP-TEST-ROTA"),
    )
    monkeypatch.setattr(
        AuditoriaImportacaoService,
        "obter_usuarios_validos",
        staticmethod(lambda empresa_id: {"Ana Silva", "Bruno Lima", "Caio Souza"}),
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


def _criar_client():
    app = create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": _FakeAuthService(),
            "empresa_service": _FakeEmpresaService(),
            "ativos_service": _DummyAtivosService(),
            "ativos_arquivo_service": _DummyArquivosService(),
        },
    )
    client = app.test_client()
    with client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
        session_data["user_perfil"] = "usuario"
        session_data["user_empresa_id"] = 10
        session_data["user_empresa_nome"] = "Empresa Demo"

    client.environ_base["HTTP_X_CSRF_TOKEN"] = _gerar_token_csrf(app, user_id=1)
    client.environ_base["HTTP_X_REQUESTED_WITH"] = "fetch"
    return app, client


def _mapear_linha_quebrado(_self, row, matches):
    linha_mapeada = {}
    for match in matches:
        if not getattr(match, "campo_destino", None):
            continue
        valor_original = row.get(match.coluna_origem, "").strip()
        if valor_original:
            linha_mapeada[match.campo_destino] = valor_original
    return linha_mapeada


def test_rota_preview_real_mesmo_caminho_da_tela_retorna_linhas_validas(monkeypatch):
    _stub_auditoria(monkeypatch)
    _app, client = _criar_client()

    response = client.post(
        "/ativos/importar/preview",
        data={"file": (BytesIO(CSV_EXPORTADO_SISTEMA), "ativos_export_20260428_114556.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200

    payload = response.get_json()
    assert payload["ok"] is True

    preview = payload["preview"]
    detalhes = preview["validacao_detalhes"]
    linhas_revisao = preview["linhas_revisao"]

    assert detalhes["total_linhas"] == 3
    assert detalhes["linhas_validas"] > 0
    assert detalhes["linhas_com_erro"] == 0
    assert all(item["tem_erro"] is False for item in linhas_revisao)

    primeira_linha = linhas_revisao[0]["dados_mapeados"]
    segunda_linha = linhas_revisao[1]["dados_mapeados"]
    terceira_linha = linhas_revisao[2]["dados_mapeados"]

    assert primeira_linha["status"] == "Disponível"
    assert primeira_linha["setor"] == "T.I"
    assert primeira_linha["tipo_ativo"] == "Notebook"

    assert segunda_linha["status"] == "Em Uso"
    assert segunda_linha["setor"] == "Rh"
    assert segunda_linha["tipo_ativo"] == "Monitor"

    assert terceira_linha["status"] == "Reservado"
    assert terceira_linha["setor"] == "Marketing"
    assert terceira_linha["tipo_ativo"] == "Celular"

    assert preview["erros_por_linha"] == []


def test_rota_preview_real_reproduz_100_por_cento_invalido_com_mapeamento_antigo(monkeypatch):
    _stub_auditoria(monkeypatch)
    monkeypatch.setattr(
        ServicoImportacaoComSeguranca,
        "_mapear_linha",
        _mapear_linha_quebrado,
    )
    _app, client = _criar_client()

    response = client.post(
        "/ativos/importar/preview",
        data={"file": (BytesIO(CSV_EXPORTADO_SISTEMA), "ativos_export_20260428_114556.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200

    payload = response.get_json()
    detalhes = payload["preview"]["validacao_detalhes"]
    erros = payload["preview"]["erros_por_linha"]

    assert detalhes["total_linhas"] == 3
    assert detalhes["linhas_validas"] == 0
    assert detalhes["linhas_com_erro"] == 3
    assert detalhes["linhas_invalidas"] == 3
    assert erros
    assert "tipo_ativo" in erros[0]["mensagem"]
    assert "vazio" in erros[0]["mensagem"]
