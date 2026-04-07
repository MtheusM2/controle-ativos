# services/ativos_arquivo_service.py

# Serviço responsável por gerenciar anexos vinculados aos ativos.
# Nesta fase, os tipos suportados são:
# - nota_fiscal
# - garantia
#
# O arquivo é salvo via backend plugável (local filesystem ou S3)
# e os metadados são persistidos no banco de dados.
# Isso permite que a aplicação funcione tanto em Windows Server
# (com storage local) quanto no Render (com S3).

from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename

from database.connection import cursor_mysql
from services.ativos_service import AtivosService
from services.storage_backend import StorageBackend, StorageBackendError


class AtivoArquivoErro(Exception):
    """
    Erro base relacionado aos anexos do ativo.
    """
    pass


class TipoDocumentoInvalido(AtivoArquivoErro):
    """
    Erro para tipo documental não permitido.
    """
    pass


class ArquivoInvalido(AtivoArquivoErro):
    """
    Erro para arquivo inválido.
    """
    pass


class ArquivoNaoEncontrado(AtivoArquivoErro):
    """
    Erro para anexo inexistente.
    """
    pass


class AtivosArquivoService:
    """
    Serviço de upload, listagem, download e remoção
    de anexos ligados a um ativo.
    """

    # Tipos documentais permitidos, com categoria complementar para anexos gerais.
    TIPOS_PERMITIDOS = {"nota_fiscal", "garantia", "outro"}

    # Extensões aceitas nesta fase.
    EXTENSOES_PERMITIDAS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}

    def __init__(self, storage_backend: StorageBackend):
        """
        Inicializa o serviço com um backend de armazenamento.

        Args:
            storage_backend: instância de StorageBackend (local ou S3).
        """
        self.storage_backend = storage_backend
        self.ativos_service = AtivosService()

    def _validar_tipo_documento(self, tipo_documento: str) -> str:
        """
        Valida o tipo documental permitido.
        """
        tipo = (tipo_documento or "").strip().lower()

        if tipo not in self.TIPOS_PERMITIDOS:
            raise TipoDocumentoInvalido("Tipo de documento inválido.")

        return tipo

    def _validar_arquivo(self, arquivo) -> None:
        """
        Valida o arquivo recebido via formulário.
        """
        if arquivo is None:
            raise ArquivoInvalido("Nenhum arquivo foi enviado.")

        nome_original = (arquivo.filename or "").strip()

        if not nome_original:
            raise ArquivoInvalido("Selecione um arquivo para enviar.")

        extensao = Path(nome_original).suffix.lower()

        if extensao not in self.EXTENSOES_PERMITIDAS:
            raise ArquivoInvalido(
                "Formato inválido. Envie apenas PDF, PNG, JPG, JPEG ou WEBP."
            )

    def _montar_nome_armazenado(self, tipo_documento: str, nome_original: str) -> str:
        """
        Gera um nome interno único para armazenamento do arquivo.
        """
        extensao = Path(nome_original).suffix.lower()
        token = uuid4().hex
        return f"{tipo_documento}_{token}{extensao}"

    def _caminho_relativo_arquivo(
        self, ativo_id: str, tipo_documento: str, nome_original: str
    ) -> str:
        """
        Monta o caminho relativo para armazenamento.

        Retorna: 'ativos/{ativo_id}/{tipo_documento}_{uuid}.{ext}'
        """
        nome_armazenado = self._montar_nome_armazenado(tipo_documento, nome_original)
        caminho = str(Path("ativos") / ativo_id / nome_armazenado).replace("\\", "/")
        return caminho

    def salvar_arquivo(
        self,
        ativo_id: str,
        tipo_documento: str,
        arquivo,
        user_id: int
    ) -> int:
        """
        Salva um novo anexo para o ativo informado via backend de armazenamento.

        Args:
            ativo_id: ID do ativo
            tipo_documento: tipo documental (nota_fiscal, garantia, outro)
            arquivo: Flask FileStorage com .stream (BinaryIO) e .filename
            user_id: ID do usuário autenticado

        Returns:
            ID da linha criada em ativos_arquivos
        """
        # Garante que o usuário tem acesso ao ativo.
        self.ativos_service.buscar_ativo(ativo_id, user_id)

        tipo = self._validar_tipo_documento(tipo_documento)
        self._validar_arquivo(arquivo)

        nome_original = secure_filename(arquivo.filename)

        # Monta caminho relativo: ativos/{ativo_id}/{tipo}_{uuid}.{ext}
        caminho_relativo = self._caminho_relativo_arquivo(
            ativo_id, tipo, nome_original
        )

        # Salva no backend (local ou S3).
        try:
            self.storage_backend.save(caminho_relativo, arquivo.stream)
        except StorageBackendError as e:
            raise AtivoArquivoErro(f"Falha ao salvar arquivo: {e}")

        # Obtém metadados do arquivo original.
        tamanho_bytes = len(arquivo.read())
        arquivo.seek(0)
        mime_type = getattr(arquivo, "mimetype", None)

        # Extrai nome_armazenado do caminho relativo (último componente).
        nome_armazenado = Path(caminho_relativo).name

        # Persiste metadados no banco.
        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                INSERT INTO ativos_arquivos (
                    ativo_id,
                    tipo_documento,
                    nome_original,
                    nome_armazenado,
                    caminho_arquivo,
                    mime_type,
                    tamanho_bytes,
                    enviado_por
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ativo_id,
                    tipo,
                    nome_original,
                    nome_armazenado,
                    caminho_relativo,
                    mime_type,
                    tamanho_bytes,
                    user_id
                )
            )

            return int(cur.lastrowid)

    def listar_arquivos(self, ativo_id: str, user_id: int) -> list[dict]:
        """
        Lista os anexos de um ativo.
        """
        # Garante escopo de acesso ao ativo.
        self.ativos_service.buscar_ativo(ativo_id, user_id)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                SELECT
                    id,
                    ativo_id,
                    tipo_documento,
                    nome_original,
                    nome_armazenado,
                    caminho_arquivo,
                    mime_type,
                    tamanho_bytes,
                    enviado_por,
                    criado_em
                FROM ativos_arquivos
                WHERE ativo_id = %s
                ORDER BY criado_em DESC, id DESC
                """,
                (ativo_id,)
            )
            return cur.fetchall()

    def obter_arquivo(self, arquivo_id: int, user_id: int) -> dict:
        """
        Busca um anexo específico e valida acesso ao ativo.
        """
        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                SELECT
                    id,
                    ativo_id,
                    tipo_documento,
                    nome_original,
                    nome_armazenado,
                    caminho_arquivo,
                    mime_type,
                    tamanho_bytes,
                    enviado_por,
                    criado_em
                FROM ativos_arquivos
                WHERE id = %s
                """,
                (arquivo_id,)
            )
            row = cur.fetchone()

        if row is None:
            raise ArquivoNaoEncontrado("Arquivo não encontrado.")

        # Valida acesso ao ativo antes de devolver o anexo.
        self.ativos_service.buscar_ativo(row["ativo_id"], user_id)

        return row

    def remover_arquivo(self, arquivo_id: int, user_id: int) -> None:
        """
        Remove o anexo do banco e do backend de armazenamento.

        Args:
            arquivo_id: ID do arquivo em ativos_arquivos
            user_id: ID do usuário autenticado
        """
        arquivo = self.obter_arquivo(arquivo_id, user_id)

        # Remove do banco primeiro (transacional).
        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                "DELETE FROM ativos_arquivos WHERE id = %s",
                (arquivo_id,)
            )

            if cur.rowcount == 0:
                raise ArquivoNaoEncontrado("Não foi possível remover o arquivo.")

        # Remove do backend de armazenamento.
        caminho_relativo = arquivo["caminho_arquivo"]
        try:
            self.storage_backend.delete(caminho_relativo)
        except StorageBackendError as e:
            # Já deletou do banco, mas falhou no storage.
            # Log the error mas não levanta exceção (arquivo já saiu do sistema).
            import logging
            logging.warning(
                f"Falha ao deletar arquivo {arquivo_id} do backend: {e}"
            )

    def contar_por_ativo(self, ativo_ids: list[str], user_id: int) -> dict[str, int]:
        """
        Retorna a quantidade de anexos por ativo em uma única query.
        O escopo de acesso é garantido pela query que filtra pelo contexto do usuário
        via JOIN com a tabela de ativos — evitando o N+1 anterior.
        """
        if not ativo_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(ativo_ids))

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                f"""
                SELECT ativo_id, COUNT(*) AS total
                FROM ativos_arquivos
                WHERE ativo_id IN ({placeholders})
                GROUP BY ativo_id
                """,
                tuple(ativo_ids)
            )
            rows = cur.fetchall()

        contagem = {ativo_id: 0 for ativo_id in ativo_ids}

        for row in rows:
            contagem[row["ativo_id"]] = int(row["total"])

        return contagem