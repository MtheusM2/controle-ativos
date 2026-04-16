"""Configurações de teste para inicialização, verificação básica e isolamento da aplicação Flask."""

# pyright: reportUnusedImport=false, reportRedeclaration=false, reportMissingImports=false

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

# Adiciona raiz do projeto ao sys.path para garantir importações de módulos
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

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
    def __init__(self):
        # Armazena ativos criados durante testes para persistência
        self._ativos_criados = {}

    def listar_ativos(self, _user_id):
        return [
            SimpleNamespace(
                id_ativo="A-001",
                tipo="Notebook",
                marca="Dell",
                modelo="XPS",
                usuario_responsavel="Ana",
                departamento="TI",
                status="Em Uso",
                data_entrada="2026-04-01",
                data_saida=None,
            )
        ]

    def filtrar_ativos(self, **kwargs):
        return self.listar_ativos(kwargs.get("user_id"))

    def criar_ativo(self, ativo, _user_id):
        # Simula retorno de ID gerado automaticamente pelo backend
        # Mas também armazena o ativo para persistência em testes
        if hasattr(ativo, 'id_ativo'):
            # Converte o objeto Ativo para um SimpleNamespace para armazenar
            ativo_dict = {}
            if hasattr(ativo, '__dict__'):
                ativo_dict = ativo.__dict__.copy()
            self._ativos_criados[ativo.id_ativo] = SimpleNamespace(**ativo_dict)
        return "OPU-000001"

    def buscar_ativo(self, id_ativo, _user_id):
        # Se o ativo foi criado em testes, retorna com os dados criados
        if id_ativo in self._ativos_criados:
            return self._ativos_criados[id_ativo]

        # Padrão para compatibilidade com testes existentes
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

    def contar_por_ativo(self, ativo_ids: list[str], _user_id: int) -> dict[str, int]:
        """Retorna contagem simulada de anexos por ativo (1 por ativo)."""
        return {ativo_id: 1 for ativo_id in ativo_ids}

    def mapear_presenca_documentos(self, ativo_ids: list[str], _user_id: int) -> dict[str, dict[str, bool]]:
        """Simula presença documental em lote usando a própria lista de arquivos fake."""
        mapa = {
            ativo_id: {"nota_fiscal": False, "garantia": False}
            for ativo_id in ativo_ids
        }

        for ativo_id in ativo_ids:
            for arquivo in self.listar_arquivos(ativo_id, _user_id):
                tipo = str(arquivo.get("tipo_documento") or "")
                nome = str(arquivo.get("nome_original") or "").strip()
                if tipo in {"nota_fiscal", "garantia"} and nome:
                    mapa[ativo_id][tipo] = True

        return mapa


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

    # Aproxima o comportamento do frontend real, que sempre envia token CSRF em fetch mutável.
    test_client.environ_base["HTTP_X_CSRF_TOKEN"] = gerar_csrf_token_para_teste(flask_app, user_id=1)
    test_client.environ_base["HTTP_X_REQUESTED_WITH"] = "fetch"
    return test_client


def gerar_csrf_token_para_teste(flask_app, user_id: int) -> str:
    """
    Gera um token CSRF válido no contexto da aplicação para uso em testes.
    O token é derivado da chave secreta e da identidade do usuário.
    """
    from itsdangerous import URLSafeTimedSerializer

    with flask_app.app_context():
        serializer = URLSafeTimedSerializer(flask_app.config["SECRET_KEY"], salt="csrf")
        return serializer.dumps(f"user:{user_id}")


def gerar_headers_csrf_para_teste(flask_app, user_id: int) -> dict[str, str]:
    """
    Retorna headers padrão de requisições fetch autenticadas para testes HTTP.
    """
    return {
        "X-CSRF-Token": gerar_csrf_token_para_teste(flask_app, user_id=user_id),
        "X-Requested-With": "fetch",
    }


def aplicar_headers_csrf_no_client_teste(test_client, flask_app, user_id: int) -> None:
    """
    Aplica headers padrão de CSRF diretamente no client de teste para requests mutáveis.
    """
    headers = gerar_headers_csrf_para_teste(flask_app, user_id=user_id)
    test_client.environ_base["HTTP_X_CSRF_TOKEN"] = headers["X-CSRF-Token"]
    test_client.environ_base["HTTP_X_REQUESTED_WITH"] = headers["X-Requested-With"]