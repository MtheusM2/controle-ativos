"""Test fixtures para bootstrap, smoke test e isolamento da app Flask."""

# pyright: reportUnusedImport=false, reportRedeclaration=false, reportMissingImports=false

from __future__ import annotations

import os
from types import SimpleNamespace


# Define valores de ambiente antes de importar a app para evitar falhas no config.
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")
os.environ.setdefault("APP_PEPPER", "test-pepper")
os.environ.setdefault("FLASK_DEBUG", "1")
os.environ.setdefault("SESSION_COOKIE_SECURE", "0")

import pytest

from web_app.app import create_app


class FakeAuthService:
    def __init__(self):
        self.user_data = {
            "id": 1,
            "nome": "Usuario Demo",
            "email": "user@example.com",
            "perfil": "usuario",
            "empresa_id": 10,
            "empresa_nome": "Empresa Demo",
            "lembrar_me_ativo": False,
            "senha": "secret",
        }

    def autenticar(self, email: str, senha: str):
        if email != self.user_data["email"] or senha != self.user_data["senha"]:
            from services.auth_service import CredenciaisInvalidas

            raise CredenciaisInvalidas("E-mail ou senha invalidos.")

        return SimpleNamespace(
            id=self.user_data["id"],
            nome=self.user_data["nome"],
            email=self.user_data["email"],
            perfil=self.user_data["perfil"],
            empresa_id=self.user_data["empresa_id"],
            empresa_nome=self.user_data["empresa_nome"],
            lembrar_me_ativo=self.user_data["lembrar_me_ativo"],
        )

    def registrar_usuario(self, **_kwargs):
        return 1

    def obter_usuario_por_id(self, _user_id: int):
        return {
            "id": self.user_data["id"],
            "nome": self.user_data["nome"],
            "email": self.user_data["email"],
            "perfil": self.user_data["perfil"],
            "empresa_id": self.user_data["empresa_id"],
            "empresa_nome": self.user_data["empresa_nome"],
            "lembrar_me_ativo": self.user_data["lembrar_me_ativo"],
            "suporta_nome": True,
            "suporta_lembrar_me": True,
        }

    def atualizar_preferencia_lembrar_me(self, _user_id: int, ativo: bool):
        self.user_data["lembrar_me_ativo"] = bool(ativo)
        return None

    def atualizar_proprio_perfil(self, _user_id: int, nome: str, email: str | None = None):
        self.user_data["nome"] = nome
        if email and email != self.user_data["email"] and self.user_data["perfil"] not in {"adm", "admin"}:
            from services.auth_service import PermissaoAuthNegada

            raise PermissaoAuthNegada("Apenas administradores podem alterar o e-mail.")

        if email:
            self.user_data["email"] = email
        return self.obter_usuario_por_id(_user_id)

    def alterar_senha_propria(self, _user_id: int, senha_atual: str, nova_senha: str):
        if senha_atual != self.user_data["senha"]:
            from services.auth_service import CredenciaisInvalidas

            raise CredenciaisInvalidas("Senha atual invalida.")
        self.user_data["senha"] = nova_senha
        return None

    def obter_pergunta_recuperacao(self, _email: str):
        return "Pergunta de seguranca?"

    def redefinir_senha(self, **_kwargs):
        return None


class FakeEmpresaService:
    def listar_empresas_ativas(self):
        return [SimpleNamespace(id=10, nome="Empresa Demo")]


class FakeAtivosService:
    def listar_ativos(self, _user_id):
        return [
            SimpleNamespace(
                id_ativo="A-001",
                tipo="Notebook",
                marca="Dell",
                modelo="XPS",
                usuario_responsavel="Ana",
                departamento="TI",
                status="Ativo",
                data_entrada="2026-04-01",
                data_saida=None,
            )
        ]

    def filtrar_ativos(self, **kwargs):
        return self.listar_ativos(kwargs.get("user_id"))

    def criar_ativo(self, _ativo, _user_id):
        return None

    def buscar_ativo(self, id_ativo, _user_id):
        return SimpleNamespace(
            id_ativo=id_ativo,
            tipo="Notebook",
            marca="Dell",
            modelo="XPS",
            usuario_responsavel="Ana",
            departamento="TI",
            status="Ativo",
            data_entrada="2026-04-01",
            data_saida=None,
        )

    def atualizar_ativo(self, **kwargs):
        return self.buscar_ativo(kwargs["id_ativo"], kwargs["user_id"])

    def remover_ativo(self, _id_ativo, _user_id):
        return None


class FakeArquivosService:
    upload_base_dir = "."

    def listar_arquivos(self, id_ativo, _user_id):
        return [
            {
                "id": 7,
                "ativo_id": id_ativo,
                "tipo_documento": "nota_fiscal",
                "nome_original": "nf.pdf",
                "tamanho_bytes": 1024,
                "mime_type": "application/pdf",
                "criado_em": "2026-04-01",
            }
        ]

    def salvar_arquivo(self, **_kwargs):
        return 7

    def obter_arquivo(self, _arquivo_id, _user_id):
        return {
            "caminho_arquivo": "uploads/nf.pdf",
            "nome_original": "nf.pdf",
            "mime_type": "application/pdf",
        }

    def remover_arquivo(self, _arquivo_id, _user_id):
        return None


@pytest.fixture()
def app_fixture():
    return create_app(
        {"TESTING": True, "DEBUG": True},
        {
            "auth_service": FakeAuthService(),
            "empresa_service": FakeEmpresaService(),
            "ativos_service": FakeAtivosService(),
            "ativos_arquivo_service": FakeArquivosService(),
        },
    )


@pytest.fixture()
def http_client(request):
    flask_app = request.getfixturevalue("app_fixture")
    return flask_app.test_client()


@pytest.fixture()
def authenticated_client(request):
    flask_app = request.getfixturevalue("app_fixture")
    test_client = flask_app.test_client()
    with test_client.session_transaction() as session_data:
        session_data["user_id"] = 1
        session_data["user_email"] = "user@example.com"
        session_data["user_perfil"] = "usuario"
        session_data["user_empresa_id"] = 10
        session_data["user_empresa_nome"] = "Empresa Demo"
    return test_client