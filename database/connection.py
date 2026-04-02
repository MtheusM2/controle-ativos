# Importa o decorador para criar context managers com "with".
from contextlib import contextmanager

# Importa o conector do MySQL.
import mysql.connector

# Importa configurações centralizadas já validadas no startup.
from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER


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