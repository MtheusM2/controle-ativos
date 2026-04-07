"""
Storage backend abstraction para suportar múltiplos ambientes de deployment.

Permite que a aplicação funcione tanto com armazenamento local (Windows)
quanto com object storage (S3-compatível) no Render, sem duplicar lógica
de arquivo nos serviços.
"""

from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Optional
from uuid import uuid4

from werkzeug.utils import secure_filename


class StorageBackendError(Exception):
    """Erro base para operações de armazenamento."""
    pass


class StorageBackend(ABC):
    """
    Interface abstrata para backends de armazenamento.

    Todos os backends devem implementar:
    - save() — salva arquivo e retorna caminho/chave para recuperação
    - load() — carrega arquivo por chave
    - delete() — remove arquivo
    - get_download_url() — retorna URL pública ou assinada para download
    """

    @abstractmethod
    def save(self, relative_path: str, file_obj: BinaryIO) -> str:
        """
        Salva arquivo e retorna chave/caminho para recuperação futura.

        Args:
            relative_path: caminho relativo (ex: 'ativos/NTB-001/nota_fiscal_uuid.pdf')
            file_obj: objeto aberto (Flask FileStorage.stream)

        Returns:
            Chave única para recuperação (pode ser igual a relative_path em local,
            ou S3 key em object storage)
        """
        pass

    @abstractmethod
    def load(self, storage_key: str) -> BytesIO:
        """
        Carrega arquivo por chave e retorna BytesIO para Flask send_file().

        Args:
            storage_key: chave retornada por save()

        Returns:
            BytesIO pronto para ser passado a Flask send_file()

        Raises:
            StorageBackendError: se arquivo não existir
        """
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """
        Remove arquivo do armazenamento.

        Args:
            storage_key: chave retornada por save()
        """
        pass

    @abstractmethod
    def get_download_url(self, storage_key: str, expires_in_seconds: int = 3600) -> str:
        """
        Retorna URL para download direto (local) ou assinada (S3).

        Args:
            storage_key: chave retornada por save()
            expires_in_seconds: tempo de validade (usado em S3; ignorado em local)

        Returns:
            URL absoluta (local) ou assinada (S3)
        """
        pass


class LocalStorageBackend(StorageBackend):
    """
    Backend para armazenamento em filesystem local.

    Usado em desenvolvimento e Windows Server. Salva arquivos
    em `base_dir/relative_path` e serve via Flask.
    """

    def __init__(self, base_dir: str):
        """
        Inicializa backend local.

        Args:
            base_dir: diretório-base (ex: 'web_app/static/uploads')
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, relative_path: str, file_obj: BinaryIO) -> str:
        """Salva arquivo em filesystem; retorna relative_path."""
        caminho_completo = self.base_dir / relative_path

        # Garante que diretório-pai existe
        caminho_completo.parent.mkdir(parents=True, exist_ok=True)

        file_obj.seek(0)
        with open(caminho_completo, "wb") as f:
            f.write(file_obj.read())

        return relative_path

    def load(self, storage_key: str) -> BytesIO:
        """Carrega arquivo do filesystem."""
        caminho_completo = self.base_dir / storage_key

        if not caminho_completo.exists():
            raise StorageBackendError(f"Arquivo não encontrado: {storage_key}")

        with open(caminho_completo, "rb") as f:
            return BytesIO(f.read())

    def delete(self, storage_key: str) -> None:
        """Remove arquivo do filesystem."""
        caminho_completo = self.base_dir / storage_key
        caminho_completo.unlink(missing_ok=True)

    def get_download_url(self, storage_key: str, expires_in_seconds: int = 3600) -> str:
        """
        Retorna URL relativa para Flask serve via send_file().

        Em produção Windows com IIS, IIS serve arquivos static/ diretamente.
        Em desenvolvimento, Flask serve via /static/ route.
        """
        # URL relativa desde a raiz do site
        return f"/static/uploads/{storage_key}"


class S3StorageBackend(StorageBackend):
    """
    Backend para Amazon S3 (ou compatível: Cloudflare R2, Backblaze B2).

    Usado no Render. Uploads vão direto para S3; downloads retornam
    URLs assinadas temporárias.
    """

    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        access_key_id: str = "",
        secret_access_key: str = "",
        endpoint_url: Optional[str] = None,
    ):
        """
        Inicializa backend S3.

        Args:
            bucket_name: nome do bucket S3
            region: região AWS (ex: 'us-east-1')
            access_key_id: chave de acesso
            secret_access_key: chave secreta
            endpoint_url: URL customizada (para R2, B2, etc.). Se None, usa AWS.
        """
        # Importação lazy de boto3 — só necessário se usar S3.
        try:
            import boto3
        except ImportError:
            raise StorageBackendError(
                "boto3 é obrigatório para usar S3StorageBackend. "
                "Instale com: pip install boto3"
            )

        self.bucket_name = bucket_name
        self.region = region
        self.endpoint_url = endpoint_url

        kwargs = {
            "region_name": region,
            "aws_access_key_id": access_key_id,
            "aws_secret_access_key": secret_access_key,
        }
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url

        try:
            self.s3_client = boto3.client("s3", **kwargs)
        except Exception as e:
            raise StorageBackendError(f"Falha ao conectar ao S3: {e}")

    def save(self, relative_path: str, file_obj: BinaryIO) -> str:
        """
        Salva arquivo em S3. Retorna S3 key (mesma que relative_path).
        """
        file_obj.seek(0)

        try:
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                relative_path,
                ExtraArgs={"ContentType": self._guess_content_type(relative_path)},
            )
        except Exception as e:
            raise StorageBackendError(f"Falha ao fazer upload para S3: {e}")

        return relative_path

    def load(self, storage_key: str) -> BytesIO:
        """Carrega arquivo do S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=storage_key,
            )
            return BytesIO(response["Body"].read())
        except self.s3_client.exceptions.NoSuchKey:
            raise StorageBackendError(f"Arquivo não encontrado em S3: {storage_key}")
        except Exception as e:
            raise StorageBackendError(f"Falha ao baixar de S3: {e}")

    def delete(self, storage_key: str) -> None:
        """Remove arquivo do S3."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=storage_key,
            )
        except Exception as e:
            raise StorageBackendError(f"Falha ao deletar de S3: {e}")

    def get_download_url(self, storage_key: str, expires_in_seconds: int = 3600) -> str:
        """
        Retorna URL assinada (presigned URL) válida por `expires_in_seconds`.

        URLs assinadas expiram automaticamente, ideal para arquivos sensíveis.
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": storage_key,
                },
                ExpiresIn=expires_in_seconds,
            )
            return url
        except Exception as e:
            raise StorageBackendError(f"Falha ao gerar presigned URL: {e}")

    @staticmethod
    def _guess_content_type(filename: str) -> str:
        """Mapeia extensão para MIME type."""
        ext_to_mime = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }
        ext = Path(filename).suffix.lower()
        return ext_to_mime.get(ext, "application/octet-stream")
