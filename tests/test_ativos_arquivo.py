"""Testes para upload, validação e gerenciamento de anexos de ativos."""

from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import pytest

from services.ativos_arquivo_service import (
    AtivosArquivoService,
    ArquivoInvalido,
    ArquivoNaoEncontrado,
    TipoDocumentoInvalido,
    calcular_status_garantia,
)


class FakeCursor:
    def __init__(self, fetchall_queue=None):
        self.fetchall_queue = list(fetchall_queue or [])
        self.statements = []
        self.rowcount = 0
        self.lastrowid = 1

    def execute(self, _sql, _params=None):
        self.statements.append((_sql, _params))
        return None

    def fetchall(self):
        if self.fetchall_queue:
            return self.fetchall_queue.pop(0)
        return []

    def fetchone(self):
        linhas = self.fetchall()
        return linhas[0] if linhas else None


class FakeCursorContext:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return None, self.cursor

    def __exit__(self, exc_type, exc, tb):
        return False


class TestValidacaoArquivo:
    """Testes para validação de arquivo no serviço."""

    def setup_method(self):
        """Configura fixtures antes de cada teste."""
        self.storage_backend = MagicMock()
        self.ativos_service = MagicMock()
        self.service = AtivosArquivoService(self.storage_backend)
        self.service.ativos_service = self.ativos_service

    def test_arquivo_nao_enviado(self):
        """Deve rejeitar quando nenhum arquivo é enviado."""
        with pytest.raises(ArquivoInvalido, match="Nenhum arquivo foi enviado"):
            self.service._validar_arquivo(None)

    def test_arquivo_sem_nome(self):
        """Deve rejeitar arquivo sem nome."""
        arquivo = MagicMock()
        arquivo.filename = ""

        with pytest.raises(ArquivoInvalido, match="Selecione um arquivo"):
            self.service._validar_arquivo(arquivo)

    def test_arquivo_extensao_invalida(self):
        """Deve rejeitar extensão não permitida."""
        arquivo = MagicMock()
        arquivo.filename = "documento.docx"
        arquivo.seek = MagicMock()
        arquivo.tell = MagicMock(return_value=1024)

        with pytest.raises(ArquivoInvalido, match="Formato inválido"):
            self.service._validar_arquivo(arquivo)

    def test_arquivo_vazio(self):
        """Deve rejeitar arquivo vazio."""
        arquivo = MagicMock()
        arquivo.filename = "documento.pdf"
        arquivo.seek = MagicMock()
        arquivo.tell = MagicMock(return_value=0)

        with pytest.raises(ArquivoInvalido, match="Arquivo vazio"):
            self.service._validar_arquivo(arquivo)

    def test_arquivo_acima_tamanho_maximo(self):
        """Deve rejeitar arquivo acima de 10 MB."""
        arquivo = MagicMock()
        arquivo.filename = "documento.pdf"

        # Simula arquivo de 15 MB
        tamanho_invalido = 15 * 1024 * 1024
        arquivo.seek = MagicMock()
        arquivo.tell = MagicMock(return_value=tamanho_invalido)

        with pytest.raises(ArquivoInvalido, match="Arquivo muito grande"):
            self.service._validar_arquivo(arquivo)

    def test_arquivo_mimetype_incorreto(self):
        """Deve rejeitar arquivo com mimetype incorreto para a extensão."""
        arquivo = MagicMock()
        arquivo.filename = "documento.pdf"
        arquivo.mimetype = "image/png"  # Incorreto para PDF
        arquivo.seek = MagicMock()
        arquivo.tell = MagicMock(return_value=1024)

        with pytest.raises(ArquivoInvalido, match="Tipo de arquivo inválido"):
            self.service._validar_arquivo(arquivo)

    def test_arquivo_valido_retorna_tamanho(self):
        """Deve retornar tamanho de arquivo válido."""
        arquivo = MagicMock()
        arquivo.filename = "documento.pdf"
        arquivo.mimetype = "application/pdf"
        tamanho_esperado = 5 * 1024 * 1024  # 5 MB
        arquivo.seek = MagicMock()
        arquivo.tell = MagicMock(return_value=tamanho_esperado)

        tamanho = self.service._validar_arquivo(arquivo)

        assert tamanho == tamanho_esperado

    def test_arquivo_sem_mimetype_permitido(self):
        """Deve aceitar arquivo sem mimetype (informação não confiável)."""
        arquivo = MagicMock()
        arquivo.filename = "documento.pdf"
        arquivo.mimetype = None
        arquivo.seek = MagicMock()
        arquivo.tell = MagicMock(return_value=1024)

        # Não deve lançar exceção
        tamanho = self.service._validar_arquivo(arquivo)
        assert tamanho == 1024

    def test_arquivo_png_com_mimetype_correto(self):
        """Deve aceitar PNG com mimetype correto."""
        arquivo = MagicMock()
        arquivo.filename = "imagem.png"
        arquivo.mimetype = "image/png"
        arquivo.seek = MagicMock()
        arquivo.tell = MagicMock(return_value=2048)

        tamanho = self.service._validar_arquivo(arquivo)
        assert tamanho == 2048

    def test_arquivo_jpeg_com_mimetype_image_jpeg(self):
        """Deve aceitar JPEG com mimetype image/jpeg."""
        arquivo = MagicMock()
        arquivo.filename = "foto.jpeg"
        arquivo.mimetype = "image/jpeg"
        arquivo.seek = MagicMock()
        arquivo.tell = MagicMock(return_value=3000)

        tamanho = self.service._validar_arquivo(arquivo)
        assert tamanho == 3000


class TestValidacaoTipoDocumento:
    """Testes para validação de tipo de documento."""

    def setup_method(self):
        """Configura fixtures antes de cada teste."""
        self.storage_backend = MagicMock()
        self.ativos_service = MagicMock()
        self.service = AtivosArquivoService(self.storage_backend)
        self.service.ativos_service = self.ativos_service

    def test_tipo_documento_invalido(self):
        """Deve rejeitar tipo de documento inválido."""
        with pytest.raises(TipoDocumentoInvalido, match="Tipo de documento inválido"):
            self.service._validar_tipo_documento("tipo_invalido")

    def test_tipo_documento_nota_fiscal(self):
        """Deve aceitar tipo 'nota_fiscal'."""
        tipo = self.service._validar_tipo_documento("nota_fiscal")
        assert tipo == "nota_fiscal"

    def test_tipo_documento_garantia(self):
        """Deve aceitar tipo 'garantia'."""
        tipo = self.service._validar_tipo_documento("garantia")
        assert tipo == "garantia"

    def test_tipo_documento_outro(self):
        """Deve aceitar tipo 'outro'."""
        tipo = self.service._validar_tipo_documento("outro")
        assert tipo == "outro"

    def test_tipo_documento_case_insensitive(self):
        """Deve converter tipo para minúsculas."""
        tipo = self.service._validar_tipo_documento("NOTA_FISCAL")
        assert tipo == "nota_fiscal"

    def test_tipo_documento_com_espacos(self):
        """Deve remover espaços do tipo."""
        tipo = self.service._validar_tipo_documento("  garantia  ")
        assert tipo == "garantia"


class TestRotasUpload:
    """Testes para rota de upload de anexos."""

    def test_upload_sem_arquivo(self, authenticated_client):
        """Deve rejeitar upload sem arquivo."""
        response = authenticated_client.post(
            "/ativos/A-001/anexos",
            data={"type": "nota_fiscal"}
        )

        assert response.status_code == 400
        json_response = response.get_json()
        assert not json_response["ok"]
        assert "arquivo" in json_response["erro"].lower()

    def test_upload_tipo_documento_invalido(self, authenticated_client):
        """Deve rejeitar tipo de documento inválido na rota."""
        arquivo_bytes = BytesIO(b"PDF content")

        response = authenticated_client.post(
            "/ativos/A-001/anexos",
            data={
                "type": "tipo_invalido",
                "file": (arquivo_bytes, "documento.pdf")
            }
        )

        assert response.status_code == 400
        json_response = response.get_json()
        assert not json_response["ok"]
        assert "tipo de documento inválido" in json_response["erro"].lower()

    def test_upload_tipo_documento_vazio(self, authenticated_client):
        """Deve rejeitar quando tipo de documento está vazio."""
        arquivo_bytes = BytesIO(b"PDF content")

        response = authenticated_client.post(
            "/ativos/A-001/anexos",
            data={
                "type": "",
                "file": (arquivo_bytes, "documento.pdf")
            }
        )

        assert response.status_code == 400
        json_response = response.get_json()
        assert not json_response["ok"]
        assert "tipo de documento" in json_response["erro"].lower()

    def test_upload_sucesso_autenticado(self, authenticated_client):
        """Deve fazer upload com sucesso quando autenticado."""
        arquivo_bytes = BytesIO(b"PDF content here")
        arquivo_bytes.seek(0)

        response = authenticated_client.post(
            "/ativos/A-001/anexos",
            data={
                "type": "nota_fiscal",
                "file": (arquivo_bytes, "documento.pdf", "application/pdf")
            },
            content_type="multipart/form-data"
        )

        assert response.status_code == 201
        json_response = response.get_json()
        assert json_response["ok"]
        assert "arquivo_id" in json_response

    def test_upload_garantia_envia_metadados_para_o_servico(self):
        from web_app.app import create_app
        from tests.conftest import FakeAtivosService, FakeAuthService, FakeEmpresaService, aplicar_headers_csrf_no_client_teste

        class FakeArquivosCapturaGarantia:
            upload_base_dir = "."

            def __init__(self):
                self.kwargs_recebidos = None

            def salvar_arquivo(self, **kwargs):
                self.kwargs_recebidos = kwargs
                return 77

            def listar_arquivos(self, _id_ativo, _user_id):
                return []

            def obter_arquivo(self, _arquivo_id, _user_id):
                return {"caminho_arquivo": "", "nome_original": "", "mime_type": ""}

            def remover_arquivo(self, _arquivo_id, _user_id):
                return None

        fake_arquivos = FakeArquivosCapturaGarantia()
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

        response = client.post(
            "/ativos/A-001/anexos",
            data={
                "type": "garantia",
                "data_inicio_garantia": "2026-04-01",
                "data_fim_garantia": "2026-05-01",
                "observacao_garantia": "Cobertura padrão",
                "file": (BytesIO(b"PDF content here"), "garantia.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 201
        assert fake_arquivos.kwargs_recebidos is not None
        assert fake_arquivos.kwargs_recebidos["metadata_garantia"]["data_inicio_garantia"] == "2026-04-01"
        assert fake_arquivos.kwargs_recebidos["metadata_garantia"]["data_fim_garantia"] == "2026-05-01"

    def test_upload_sem_sessao(self, http_client):
        """Deve rejeitar upload sem sessão autenticada."""
        arquivo_bytes = BytesIO(b"PDF content")

        response = http_client.post(
            "/ativos/A-001/anexos",
            data={
                "type": "nota_fiscal",
                "file": (arquivo_bytes, "documento.pdf")
            }
        )

        assert response.status_code == 401
        json_response = response.get_json()
        assert not json_response["ok"]
        assert "sessão" in json_response["erro"].lower()


class TestGarantiaMetadata:
    """Testes para metadados estruturados de garantia."""

    def setup_method(self):
        self.storage_backend = MagicMock()
        self.ativos_service = MagicMock()
        self.service = AtivosArquivoService(self.storage_backend)
        self.service.ativos_service = self.ativos_service

    def test_normalizar_metadados_garantia_aceita_datas_validas(self):
        resultado = self.service._normalizar_metadados_garantia(
            "garantia",
            {
                "data_inicio_garantia": "2026-04-01",
                "data_fim_garantia": "2026-05-01",
                "prazo_garantia_meses": "12",
                "observacao_garantia": "Cobertura premium",
            },
        )

        assert resultado["data_inicio_garantia"] == "2026-04-01"
        assert resultado["data_fim_garantia"] == "2026-05-01"
        assert resultado["prazo_garantia_meses"] == 12
        assert resultado["observacao_garantia"] == "Cobertura premium"

    def test_normalizar_metadados_garantia_rejeita_data_final_menor_que_inicial(self):
        with pytest.raises(ArquivoInvalido, match="data_fim_garantia"):
            self.service._normalizar_metadados_garantia(
                "garantia",
                {
                    "data_inicio_garantia": "2026-05-10",
                    "data_fim_garantia": "2026-05-01",
                },
            )

    def test_normalizar_metadados_garantia_ignora_campos_quando_tipo_nao_e_garantia(self):
        resultado = self.service._normalizar_metadados_garantia(
            "nota_fiscal",
            {
                "data_inicio_garantia": "2026-04-01",
                "data_fim_garantia": "2026-05-01",
            },
        )

        assert resultado["data_inicio_garantia"] is None
        assert resultado["data_fim_garantia"] is None
        assert resultado["prazo_garantia_meses"] is None
        assert resultado["observacao_garantia"] is None


def test_calcular_status_garantia_retorna_ativa():
    futuro = date.today() + timedelta(days=45)
    resultado = calcular_status_garantia(futuro)

    assert resultado["status_garantia"] == "ativa"
    assert resultado["dias_restantes"] == 45
    assert resultado["vencida"] is False
    assert resultado["vencendo_em_breve"] is False


def test_calcular_status_garantia_retorna_vencendo_em_breve():
    futuro = date.today() + timedelta(days=10)
    resultado = calcular_status_garantia(futuro)

    assert resultado["status_garantia"] == "vencendo_em_breve"
    assert resultado["dias_restantes"] == 10
    assert resultado["vencendo_em_breve"] is True


def test_calcular_status_garantia_retorna_vencida():
    passado = date.today() - timedelta(days=2)
    resultado = calcular_status_garantia(passado)

    assert resultado["status_garantia"] == "vencida"
    assert resultado["dias_restantes"] == -2
    assert resultado["vencida"] is True


def test_calcular_status_garantia_sem_data_retorna_sem_garantia():
    resultado = calcular_status_garantia(None)

    assert resultado["status_garantia"] == "sem_garantia"
    assert resultado["dias_restantes"] is None


def test_listar_arquivos_tolera_schema_legado_sem_metadados_garantia(monkeypatch):
    storage_backend = MagicMock()
    service = AtivosArquivoService(storage_backend)
    service.ativos_service = MagicMock()
    service.ativos_service.buscar_ativo.return_value = SimpleNamespace(id_ativo="A-001")

    cursor = FakeCursor(
        fetchall_queue=[
            [
                {"COLUMN_NAME": "id"},
                {"COLUMN_NAME": "ativo_id"},
                {"COLUMN_NAME": "tipo_documento"},
                {"COLUMN_NAME": "nome_original"},
                {"COLUMN_NAME": "nome_armazenado"},
                {"COLUMN_NAME": "caminho_arquivo"},
                {"COLUMN_NAME": "mime_type"},
                {"COLUMN_NAME": "tamanho_bytes"},
                {"COLUMN_NAME": "enviado_por"},
                {"COLUMN_NAME": "criado_em"},
            ],
            [
                {
                    "id": 1,
                    "ativo_id": "A-001",
                    "tipo_documento": "garantia",
                    "nome_original": "garantia.pdf",
                    "nome_armazenado": "garantia_1.pdf",
                    "caminho_arquivo": "ativos/A-001/garantia_1.pdf",
                    "mime_type": "application/pdf",
                    "tamanho_bytes": 1024,
                    "enviado_por": 1,
                    "criado_em": "2026-04-30 10:00:00",
                    "data_inicio_garantia": None,
                    "data_fim_garantia": None,
                    "prazo_garantia_meses": None,
                    "observacao_garantia": None,
                }
            ],
        ]
    )

    monkeypatch.setattr(
        "services.ativos_arquivo_service.cursor_mysql",
        lambda dictionary=True: FakeCursorContext(cursor),
    )

    arquivos = service.listar_arquivos("A-001", user_id=1)

    assert len(arquivos) == 1
    assert arquivos[0]["nome_original"] == "garantia.pdf"
    assert arquivos[0]["data_inicio_garantia"] is None
    assert arquivos[0]["data_fim_garantia"] is None
