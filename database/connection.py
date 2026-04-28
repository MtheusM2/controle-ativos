# Importa o decorador para criar context managers com "with".
from contextlib import contextmanager

# Importa o conector do MySQL.
import mysql.connector

# Importa configurações centralizadas já validadas no startup.
from config import DB_CONNECTION_TIMEOUT, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER


def _db_config(com_database: bool = True) -> dict:
    """
    Monta o dicionário de configuração da conexão MySQL.

    Parâmetros:
    - com_database:
      Se True, inclui o nome do banco na conexão.
      Se False, conecta apenas ao servidor MySQL.

    Retorno:
    - dicionário com os parâmetros da conexão.
    """
    # Reutiliza valores centralizados para garantir consistência em toda a app.
    host = DB_HOST
    port = DB_PORT
    user = DB_USER
    password = DB_PASSWORD
    database = DB_NAME

    cfg = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "connection_timeout": DB_CONNECTION_TIMEOUT,
    }

    if com_database:
        cfg["database"] = database

    return cfg


@contextmanager
def conexao_mysql(com_database: bool = True):
    """
    Abre uma conexão MySQL e controla commit/rollback automaticamente.
    """
    conn = None

    try:
        conn = mysql.connector.connect(**_db_config(com_database=com_database))
        conn.autocommit = False
        yield conn
        conn.commit()

    except Exception:
        if conn is not None and conn.is_connected():
            conn.rollback()
        raise

    finally:
        if conn is not None and conn.is_connected():
            conn.close()


@contextmanager
def cursor_mysql(dictionary: bool = True):
    """
    Abre conexão e cursor padronizados para uso no projeto.
    """
    with conexao_mysql(com_database=True) as conn:
        cur = conn.cursor(dictionary=dictionary)

        try:
            yield conn, cur
        finally:
            cur.close()


def classificar_erro_conexao_mysql(error: Exception) -> str:
    """
    Converte erros MySQL em mensagens seguras para healthcheck e diagnósticos.

    A resposta nunca inclui senha, string de conexão ou stack trace.
    """
    errno = getattr(error, "errno", None)
    mensagem = str(error).strip().lower()

    if errno in {1045} or "access denied" in mensagem:
        return "Credenciais de banco invalidas ou conexao recusada"

    if errno in {1049} or "unknown database" in mensagem:
        return "Banco de dados nao encontrado ou inacessivel"

    if errno in {2002, 2003, 2006, 2013, 2055}:
        return "Banco de dados indisponivel ou conexao recusada"

    if any(palavra in mensagem for palavra in ("can't connect", "connection refused", "timed out", "timeout")):
        return "Banco de dados indisponivel ou conexao recusada"

    return "Erro ao validar a conexao com o banco de dados"


def verificar_conexao_mysql() -> None:
    """
    Executa uma consulta simples de healthcheck no MySQL.

    A excecao original sobe para que a camada HTTP registre o stack trace e
    traduza a falha em uma resposta segura.
    """
    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(**_db_config(com_database=True))
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()