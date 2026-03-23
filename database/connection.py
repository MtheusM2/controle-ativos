
import os
from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error


def _db_config(com_database: bool = True) -> dict:
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "etectcc@2026")
    database = os.getenv("DB_NAME", "controle_ativos")

    cfg = {
        "host": host,
        "port": port,
        "user": user,
        "password": password
    }

    if com_database:
        cfg["database"] = database

    return cfg


@contextmanager
def conexao_mysql(com_database: bool = True):
    conn = None
    try:
        conn = mysql.connector.connect(**_db_config(com_database=com_database))
        conn.autocommit = False
        yield conn
        conn.commit()
    except Error:
        if conn is not None:
            conn.rollback()
        raise
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if conn is not None:
            conn.close()


@contextmanager
def cursor_mysql(dictionary: bool = True):
    with conexao_mysql(com_database=True) as conn:
        cur = conn.cursor(dictionary=dictionary)
        try:
            yield conn, cur
        finally:
            cur.close()
            