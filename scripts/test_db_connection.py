"""
Teste rápido de conexão com banco usando a configuração oficial do projeto.
"""

from __future__ import annotations

import sys
from pathlib import Path

import mysql.connector

# Garante import dos módulos do projeto ao executar via "python scripts/...".
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import _db_config  # noqa: E402


def main() -> int:
    """
    Testa conexão e executa query simples de validação.
    """
    conn = None
    cursor = None

    try:
        # Usa exatamente a mesma configuração consumida pela aplicação.
        conn = mysql.connector.connect(**_db_config(com_database=True))
        cursor = conn.cursor()

        # Retorna usuário MySQL efetivo e banco selecionado na sessão.
        cursor.execute("SELECT CURRENT_USER(), DATABASE();")
        current_user, current_database = cursor.fetchone()

        print("Conexão com banco: SUCESSO")
        print(f"CURRENT_USER(): {current_user}")
        print(f"DATABASE(): {current_database}")
        return 0
    except mysql.connector.Error as exc:
        print("Conexão com banco: FALHA")
        print(f"Erro MySQL: {exc}")
        return 1
    except Exception as exc:  # pylint: disable=broad-except
        print("Conexão com banco: FALHA")
        print(f"Erro inesperado: {exc}")
        return 1
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
