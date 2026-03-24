# Importa funções para ler variáveis de ambiente do sistema operacional.
import os

# Importa o decorador que permite criar context managers com "with".
from contextlib import contextmanager

# Importa o conector do MySQL.
import mysql.connector

# Importa o carregador de arquivo .env.
from dotenv import load_dotenv

# Carrega automaticamente as variáveis definidas no arquivo .env.
# Isso permite que DB_HOST, DB_USER, DB_PASSWORD etc. sejam lidos
# mesmo ao executar o projeto localmente no Windows.
load_dotenv()


def _db_config(com_database: bool = True) -> dict:
    """
    Monta e retorna o dicionário de configuração da conexão MySQL.

    Parâmetros:
    - com_database:
      Se True, inclui o nome do banco na conexão.
      Se False, conecta apenas ao servidor MySQL.

    Retorno:
    - dict com os parâmetros aceitos pelo mysql.connector.connect()
    """
    # Lê host do banco a partir do ambiente. Se não existir, usa localhost.
    host = os.getenv("DB_HOST", "localhost")

    # Lê a porta do banco. Se não existir, usa a porta padrão do MySQL.
    port = int(os.getenv("DB_PORT", "3306"))

    # Lê o usuário do banco. Se não existir, usa root como padrão local.
    user = os.getenv("DB_USER", "root")

    # Lê a senha do banco.
    # Importante:
    # Não deixamos mais uma senha real fixa no código.
    password = os.getenv("DB_PASSWORD", "")

    # Lê o nome do banco.
    database = os.getenv("DB_NAME", "controle_ativos")

    # Monta a configuração base da conexão.
    cfg = {
        "host": host,
        "port": port,
        "user": user,
        "password": password
    }

    # Inclui o banco apenas quando necessário.
    if com_database:
        cfg["database"] = database

    return cfg


@contextmanager
def conexao_mysql(com_database: bool = True):
    """
    Abre uma conexão com o MySQL e gerencia commit/rollback automaticamente.

    Fluxo:
    - abre a conexão
    - desativa autocommit
    - entrega a conexão para o bloco 'with'
    - se tudo der certo, faz commit
    - se algo falhar, faz rollback
    - ao final, fecha a conexão
    """
    conn = None

    try:
        # Abre a conexão com base nas configurações definidas em _db_config().
        conn = mysql.connector.connect(**_db_config(com_database=com_database))

        # Desativa autocommit para controlar transação manualmente.
        conn.autocommit = False

        # Entrega a conexão para quem chamou.
        yield conn

        # Se nenhuma exceção aconteceu, confirma a transação.
        conn.commit()

    except Exception:
        # Se houver qualquer falha durante a transação, desfaz alterações.
        if conn is not None and conn.is_connected():
            conn.rollback()

        # Relança o erro original para não esconder a causa real.
        raise

    finally:
        # Garante o fechamento da conexão ao final do processo.
        if conn is not None and conn.is_connected():
            conn.close()


@contextmanager
def cursor_mysql(dictionary: bool = True):
    """
    Abre uma conexão e um cursor de forma padronizada.

    Parâmetros:
    - dictionary:
      Se True, o cursor retorna resultados como dicionário.
      Se False, retorna tuplas.

    Retorno:
    - yield (conn, cur)
    """
    with conexao_mysql(com_database=True) as conn:
        # Cria o cursor com o modo solicitado.
        cur = conn.cursor(dictionary=dictionary)

        try:
            # Entrega conexão e cursor para uso externo.
            yield conn, cur
        finally:
            # Garante o fechamento do cursor.
            cur.close()