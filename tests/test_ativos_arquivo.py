"""Testes para upload, validação e gerenciamento de anexos de ativos."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import pytest

from services.ativos_arquivo_service import (
    AtivosArquivoService,
    ArquivoInvalido,
    ArquivoNaoEncontrado,
    TipoDocumentoInvalido,
)


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
