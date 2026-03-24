# Importa funções para ler variáveis de ambiente.
import os

# Importa utilitário para trabalhar com caminhos de forma segura.
from pathlib import Path

# Importa o decorador para criar context managers com "with".
from contextlib import contextmanager

# Importa o conector do MySQL.
import mysql.connector

# Importa o carregador de variáveis de ambiente do arquivo .env.
from dotenv import load_dotenv


# =========================
# CARREGAMENTO DO ARQUIVO .ENV
# =========================
# Descobre a pasta raiz do projeto a partir deste arquivo:
# database/connection.py -> sobe um nível e encontra a raiz do projeto.
BASE_DIR = Path(__file__).resolve().parent.parent

# Monta o caminho absoluto do arquivo .env.
ENV_FILE = BASE_DIR / ".env"

# Carrega o arquivo .env de forma explícita.
# Isso evita depender do diretório atual do terminal.
load_dotenv(dotenv_path=ENV_FILE)


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
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "controle_ativos")

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