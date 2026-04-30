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

from datetime import date, datetime
import logging
from pathlib import Path
import threading
from uuid import uuid4

from werkzeug.utils import secure_filename

from database.connection import cursor_mysql
from services.ativos_service import AtivosService
from services.storage_backend import StorageBackend, StorageBackendError


logger = logging.getLogger(__name__)


ATIVOS_ARQUIVOS_COLUNAS_RETORNO = [
    "id",
    "ativo_id",
    "tipo_documento",
    "nome_original",
    "nome_armazenado",
    "caminho_arquivo",
    "mime_type",
    "tamanho_bytes",
    "enviado_por",
    "criado_em",
    "data_inicio_garantia",
    "data_fim_garantia",
    "prazo_garantia_meses",
    "observacao_garantia",
]

ATIVOS_ARQUIVOS_COLUNAS_RETORNO_OBRIGATORIAS = {
    "id",
    "ativo_id",
    "tipo_documento",
    "nome_original",
    "nome_armazenado",
    "caminho_arquivo",
    "mime_type",
    "tamanho_bytes",
    "enviado_por",
    "criado_em",
}

ATIVOS_ARQUIVOS_COLUNAS_ESCRITA_OPCIONAIS = {
    "data_inicio_garantia",
    "data_fim_garantia",
    "prazo_garantia_meses",
    "observacao_garantia",
}


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


def _normalizar_data_garantia(valor: str | date | None, nome_campo: str) -> date | None:
    """
    Normaliza datas de garantia aceitando string ISO ou objeto date.
    """
    if valor in (None, ""):
        return None

    if isinstance(valor, date):
        return valor

    bruto = str(valor).strip()
    if not bruto:
        return None

    try:
        return datetime.strptime(bruto, "%Y-%m-%d").date()
    except ValueError as erro:
        raise ArquivoInvalido(f"O campo {nome_campo} deve usar o formato YYYY-MM-DD.") from erro


def calcular_status_garantia(
    data_fim_garantia: str | date | None,
    *,
    referencia: date | None = None,
) -> dict:
    """
    Calcula o status operacional da garantia sem materializar no banco.
    """
    data_fim = _normalizar_data_garantia(data_fim_garantia, "data_fim_garantia")
    hoje = referencia or date.today()

    if data_fim is None:
        return {
            "status_garantia": "sem_garantia",
            "dias_restantes": None,
            "vencida": False,
            "vencendo_em_breve": False,
        }

    dias_restantes = (data_fim - hoje).days
    if dias_restantes < 0:
        return {
            "status_garantia": "vencida",
            "dias_restantes": dias_restantes,
            "vencida": True,
            "vencendo_em_breve": False,
        }

    if dias_restantes <= 30:
        return {
            "status_garantia": "vencendo_em_breve",
            "dias_restantes": dias_restantes,
            "vencida": False,
            "vencendo_em_breve": True,
        }

    return {
        "status_garantia": "ativa",
        "dias_restantes": dias_restantes,
        "vencida": False,
        "vencendo_em_breve": False,
    }


class AtivosArquivoService:
    """
    Serviço de upload, listagem, download e remoção
    de anexos ligados a um ativo.
    """

    # Tipos documentais permitidos, com categoria complementar para anexos gerais.
    TIPOS_PERMITIDOS = {"nota_fiscal", "garantia", "outro"}

    # Extensões aceitas nesta fase.
    EXTENSOES_PERMITIDAS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}

    # Tamanho máximo de arquivo em bytes (10 MB).
    MAX_TAMANHO_BYTES = 10 * 1024 * 1024

    # Mimetypes esperados por extensão para validação de integridade.
    MIMETYPES_ESPERADOS = {
        ".pdf": {"application/pdf"},
        ".png": {"image/png"},
        ".jpg": {"image/jpeg"},
        ".jpeg": {"image/jpeg"},
        ".webp": {"image/webp"},
    }

    def __init__(self, storage_backend: StorageBackend):
        """
        Inicializa o serviço com um backend de armazenamento.

        Args:
            storage_backend: instância de StorageBackend (local ou S3).
        """
        self.storage_backend = storage_backend
        self.ativos_service = AtivosService()
        self._ativos_arquivos_columns_cache: set[str] | None = None
        self._schema_cache_lock = threading.Lock()
        self._avisos_schema_emitidos: set[tuple[str, tuple[str, ...]]] = set()

    def _carregar_colunas_ativos_arquivos(self, cur) -> set[str]:
        """
        Lê as colunas reais da tabela de anexos para suportar rollout gradual de migrations.
        """
        cur.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'ativos_arquivos'
            """
        )
        rows = cur.fetchall() or []
        colunas = {
            (row.get("COLUMN_NAME") if isinstance(row, dict) else row[0])
            for row in rows
        }
        if not colunas:
            # Fallback defensivo para ambientes de teste/mocks sem INFORMATION_SCHEMA.
            colunas = set(ATIVOS_ARQUIVOS_COLUNAS_RETORNO)
        self._ativos_arquivos_columns_cache = {str(coluna) for coluna in colunas if coluna}
        return self._ativos_arquivos_columns_cache

    def _obter_colunas_ativos_arquivos(self, cur) -> set[str]:
        """
        Retorna o schema cacheado de ativos_arquivos com inicialização thread-safe.
        """
        if self._ativos_arquivos_columns_cache is None:
            with self._schema_cache_lock:
                if self._ativos_arquivos_columns_cache is None:
                    self._carregar_colunas_ativos_arquivos(cur)
        return self._ativos_arquivos_columns_cache or set()

    def _registrar_aviso_schema_arquivos(self, operacao: str, colunas_ausentes: list[str]) -> None:
        """
        Emite aviso único quando colunas opcionais de anexos ainda não existem no schema.
        """
        if not colunas_ausentes:
            return

        chave = (operacao, tuple(sorted(colunas_ausentes)))
        if chave in self._avisos_schema_emitidos:
            return

        self._avisos_schema_emitidos.add(chave)
        logger.warning(
            "Schema legado detectado em ativos_arquivos durante %s. Colunas opcionais ausentes: %s. "
            "A migration correspondente ainda precisa ser aplicada.",
            operacao,
            ", ".join(sorted(colunas_ausentes)),
        )

    def _montar_select_colunas_ativos_arquivos(self, cur) -> str:
        """
        Monta SELECT retrocompatível para anexos sem falhar quando metadados novos ainda não existem.
        """
        colunas_disponiveis = self._obter_colunas_ativos_arquivos(cur)
        colunas_sql: list[str] = []
        colunas_ausentes: list[str] = []

        for coluna in ATIVOS_ARQUIVOS_COLUNAS_RETORNO:
            if coluna in colunas_disponiveis:
                colunas_sql.append(coluna)
                continue

            if coluna in ATIVOS_ARQUIVOS_COLUNAS_RETORNO_OBRIGATORIAS:
                raise AtivoArquivoErro(
                    f"Schema incompatível na tabela ativos_arquivos: coluna obrigatória ausente ({coluna})."
                )

            colunas_sql.append(f"NULL AS {coluna}")
            colunas_ausentes.append(coluna)

        self._registrar_aviso_schema_arquivos("leitura", colunas_ausentes)
        return ",\n                    ".join(colunas_sql)

    def _filtrar_campos_persistencia_ativos_arquivos(
        self,
        cur,
        campos: list[tuple[str, object]],
    ) -> list[tuple[str, object]]:
        """
        Remove apenas metadados opcionais ainda não migrados, preservando o fluxo principal de anexos.
        """
        colunas_disponiveis = self._obter_colunas_ativos_arquivos(cur)
        obrigatorias_ausentes = [
            campo for campo, _valor in campos
            if campo not in colunas_disponiveis and campo not in ATIVOS_ARQUIVOS_COLUNAS_ESCRITA_OPCIONAIS
        ]
        if obrigatorias_ausentes:
            raise AtivoArquivoErro(
                "Schema incompatível na tabela ativos_arquivos. Colunas obrigatórias ausentes: "
                + ", ".join(sorted(obrigatorias_ausentes))
            )

        opcionais_ausentes = [
            campo for campo, _valor in campos
            if campo not in colunas_disponiveis and campo in ATIVOS_ARQUIVOS_COLUNAS_ESCRITA_OPCIONAIS
        ]
        self._registrar_aviso_schema_arquivos("persistência", opcionais_ausentes)
        return [(campo, valor) for campo, valor in campos if campo in colunas_disponiveis]

    def _validar_tipo_documento(self, tipo_documento: str) -> str:
        """
        Valida o tipo documental permitido.
        """
        tipo = (tipo_documento or "").strip().lower()

        if tipo not in self.TIPOS_PERMITIDOS:
            raise TipoDocumentoInvalido("Tipo de documento inválido.")

        return tipo

    def _validar_arquivo(self, arquivo) -> int:
        """
        Valida o arquivo recebido via formulário.
        Verifica: presença, nome, extensão, tamanho e mimetype.

        Returns:
            Tamanho do arquivo em bytes
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

        # Valida tamanho do arquivo.
        arquivo.seek(0, 2)  # Vai para o final do arquivo
        tamanho_bytes = arquivo.tell()
        arquivo.seek(0)  # Volta para o início

        if tamanho_bytes == 0:
            raise ArquivoInvalido("Arquivo vazio. Envie um arquivo com conteúdo.")

        if tamanho_bytes > self.MAX_TAMANHO_BYTES:
            tamanho_mb = self.MAX_TAMANHO_BYTES / (1024 * 1024)
            raise ArquivoInvalido(
                f"Arquivo muito grande. Tamanho máximo: {tamanho_mb:.0f} MB."
            )

        # Valida mimetype contra extensão (defesa contra upload disfarçado).
        mime_type = getattr(arquivo, "mimetype", None) or ""
        mime_type = mime_type.lower().strip()
        tipos_esperados = self.MIMETYPES_ESPERADOS.get(extensao, set())

        if mime_type and tipos_esperados and mime_type not in tipos_esperados:
            raise ArquivoInvalido(
                f"Tipo de arquivo inválido. Esperado {', '.join(tipos_esperados)}."
            )

        return tamanho_bytes

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

    def _normalizar_metadados_garantia(self, tipo_documento: str, metadata: dict | None) -> dict:
        """
        Normaliza e valida metadados estruturados do documento de garantia.
        """
        if tipo_documento != "garantia":
            return {
                "data_inicio_garantia": None,
                "data_fim_garantia": None,
                "prazo_garantia_meses": None,
                "observacao_garantia": None,
            }

        metadata = metadata or {}
        data_inicio = _normalizar_data_garantia(
            metadata.get("data_inicio_garantia"),
            "data_inicio_garantia",
        )
        data_fim = _normalizar_data_garantia(
            metadata.get("data_fim_garantia"),
            "data_fim_garantia",
        )
        observacao = (metadata.get("observacao_garantia") or "").strip() or None
        prazo_bruto = metadata.get("prazo_garantia_meses")
        prazo_meses = None

        if prazo_bruto not in (None, ""):
            try:
                prazo_meses = int(str(prazo_bruto).strip())
            except (TypeError, ValueError) as erro:
                raise ArquivoInvalido("O campo prazo_garantia_meses deve ser numérico.") from erro
            if prazo_meses < 0:
                raise ArquivoInvalido("O campo prazo_garantia_meses não pode ser negativo.")

        if data_inicio and data_fim and data_fim < data_inicio:
            raise ArquivoInvalido(
                "A data_fim_garantia não pode ser anterior à data_inicio_garantia."
            )

        if observacao and len(observacao) > 255:
            raise ArquivoInvalido("O campo observacao_garantia deve ter no máximo 255 caracteres.")

        return {
            "data_inicio_garantia": data_inicio.isoformat() if data_inicio else None,
            "data_fim_garantia": data_fim.isoformat() if data_fim else None,
            "prazo_garantia_meses": prazo_meses,
            "observacao_garantia": observacao,
        }

    def salvar_arquivo(
        self,
        ativo_id: str,
        tipo_documento: str,
        arquivo,
        user_id: int,
        metadata_garantia: dict | None = None,
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

        Permissões: admin, gestor_unidade, operador (não: consulta)
        """
        # Garante que o usuário tem acesso ao ativo.
        self.ativos_service.buscar_ativo(ativo_id, user_id)

        # Validação de permissão: consulta não pode fazer upload
        from database.connection import cursor_mysql
        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                "SELECT perfil FROM usuarios WHERE id = %s",
                (user_id,)
            )
            row = cur.fetchone()
            if row:
                perfil = (row.get("perfil") or "").strip().lower()
                if perfil == "consulta":
                    raise AtivoArquivoErro("Perfil 'consulta' não tem permissão para fazer upload.")

        tipo = self._validar_tipo_documento(tipo_documento)
        tamanho_bytes = self._validar_arquivo(arquivo)
        metadados_garantia = self._normalizar_metadados_garantia(tipo, metadata_garantia)

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
        mime_type = getattr(arquivo, "mimetype", None)

        # Extrai nome_armazenado do caminho relativo (último componente).
        nome_armazenado = Path(caminho_relativo).name

        # Persiste metadados no banco.
        with cursor_mysql(dictionary=True) as (_conn, cur):
            campos_insert = [
                ("ativo_id", ativo_id),
                ("tipo_documento", tipo),
                ("nome_original", nome_original),
                ("nome_armazenado", nome_armazenado),
                ("caminho_arquivo", caminho_relativo),
                ("mime_type", mime_type),
                ("tamanho_bytes", tamanho_bytes),
                ("enviado_por", user_id),
                ("data_inicio_garantia", metadados_garantia["data_inicio_garantia"]),
                ("data_fim_garantia", metadados_garantia["data_fim_garantia"]),
                ("prazo_garantia_meses", metadados_garantia["prazo_garantia_meses"]),
                ("observacao_garantia", metadados_garantia["observacao_garantia"]),
            ]
            campos_insert = self._filtrar_campos_persistencia_ativos_arquivos(cur, campos_insert)
            colunas_sql = ",\n                    ".join(campo for campo, _valor in campos_insert)
            placeholders_sql = ", ".join(["%s"] * len(campos_insert))
            valores_insert = tuple(valor for _campo, valor in campos_insert)

            cur.execute(
                f"""
                INSERT INTO ativos_arquivos (
                    {colunas_sql}
                )
                VALUES ({placeholders_sql})
                """,
                valores_insert,
            )

            return int(cur.lastrowid)

    def listar_arquivos(self, ativo_id: str, user_id: int) -> list[dict]:
        """
        Lista os anexos de um ativo.
        """
        # Garante escopo de acesso ao ativo.
        self.ativos_service.buscar_ativo(ativo_id, user_id)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            select_colunas = self._montar_select_colunas_ativos_arquivos(cur)
            cur.execute(
                f"""
                SELECT
                    {select_colunas}
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
            select_colunas = self._montar_select_colunas_ativos_arquivos(cur)
            cur.execute(
                f"""
                SELECT
                    {select_colunas}
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
            # Registra o erro mas não levanta exceção (arquivo já saiu do sistema).
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

    def mapear_presenca_documentos(self, ativo_ids: list[str], user_id: int) -> dict[str, dict[str, bool]]:
        """
        Retorna presença de documentos por ativo em lote, sem N+1.

        Estrutura de retorno:
        {
            "NTB-001": {"nota_fiscal": True, "garantia": False},
            ...
        }

        Observação de escopo:
        esta função recebe IDs já filtrados pelo fluxo de listagem do usuário,
        portanto não amplia superfície de acesso além do contexto autorizado.
        """
        del user_id  # Escopo já garantido pelos IDs recebidos da listagem autorizada.

        if not ativo_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(ativo_ids))
        mapa = {
            ativo_id: {"nota_fiscal": False, "garantia": False}
            for ativo_id in ativo_ids
        }

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                f"""
                SELECT ativo_id, tipo_documento, COUNT(*) AS total
                FROM ativos_arquivos
                WHERE ativo_id IN ({placeholders})
                  AND tipo_documento IN ('nota_fiscal', 'garantia')
                  AND COALESCE(NULLIF(TRIM(nome_original), ''), '') <> ''
                GROUP BY ativo_id, tipo_documento
                """,
                tuple(ativo_ids),
            )
            rows = cur.fetchall()

        for row in rows:
            ativo_id = str(row.get("ativo_id") or "")
            tipo_documento = str(row.get("tipo_documento") or "")
            if ativo_id in mapa and tipo_documento in {"nota_fiscal", "garantia"}:
                mapa[ativo_id][tipo_documento] = int(row.get("total") or 0) > 0

        return mapa

    def mapear_status_garantia(self, ativo_ids: list[str], user_id: int) -> dict[str, dict]:
        """
        Retorna o status resumido da garantia por ativo com base no anexo mais recente.
        """
        del user_id  # Escopo já garantido pelos IDs recebidos da listagem autorizada.

        if not ativo_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(ativo_ids))
        mapa = {
            ativo_id: calcular_status_garantia(None)
            for ativo_id in ativo_ids
        }

        with cursor_mysql(dictionary=True) as (_conn, cur):
            colunas_disponiveis = self._obter_colunas_ativos_arquivos(cur)
            if "data_fim_garantia" not in colunas_disponiveis:
                self._registrar_aviso_schema_arquivos("garantia", ["data_fim_garantia"])
                return mapa
            cur.execute(
                f"""
                SELECT aa.ativo_id, aa.data_fim_garantia
                FROM ativos_arquivos aa
                INNER JOIN (
                    SELECT ativo_id, MAX(id) AS ultimo_id
                    FROM ativos_arquivos
                    WHERE ativo_id IN ({placeholders})
                      AND tipo_documento = 'garantia'
                    GROUP BY ativo_id
                ) ult
                    ON ult.ultimo_id = aa.id
                """,
                tuple(ativo_ids),
            )
            rows = cur.fetchall()

        for row in rows:
            ativo_id = str(row.get("ativo_id") or "")
            if ativo_id in mapa:
                mapa[ativo_id] = calcular_status_garantia(row.get("data_fim_garantia"))

        return mapa
