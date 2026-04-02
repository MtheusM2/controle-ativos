"""
Diagnóstico seguro da configuração em runtime.

Este script ajuda a confirmar quais variáveis de configuração estão sendo usadas
pela aplicação, sem vazar segredos completos no terminal/log.
"""

from __future__ import annotations

import sys
from pathlib import Path

import mysql.connector

# Garante import dos módulos do projeto ao executar via "python scripts/...".
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Importa configuração centralizada (já faz load_dotenv com override=True).
from config import (  # noqa: E402
    APP_PEPPER,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    ENV_FILE,
    FLASK_SECRET_KEY,
)
from database.connection import _db_config  # noqa: E402


def _mask_secret(value: str) -> str:
    """
    Mascara segredos exibindo apenas prefixo e sufixo.

    Exemplo:
    - "abcdef123456" -> "abc***456"
    - Strings curtas retornam máscara fixa para não expor conteúdo.
    """
    if not value:
        return "<vazio>"
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}***{value[-3:]}"


def main() -> int:
    """
    Exibe configuração efetiva e testa conectividade com o banco.
    """
    print("=== Diagnóstico de Configuração Runtime ===")
    print(f".env esperado: {ENV_FILE}")
    print(f".env existe: {'SIM' if ENV_FILE.exists() else 'NÃO'}")
    print(f"DB_HOST: {DB_HOST}")
    print(f"DB_PORT: {DB_PORT}")
    print(f"DB_USER: {DB_USER}")
    print(f"DB_NAME: {DB_NAME}")
    print(f"FLASK_SECRET_KEY: {_mask_secret(FLASK_SECRET_KEY)}")
    print(f"APP_PEPPER: {_mask_secret(APP_PEPPER)}")
    print(f"DB_PASSWORD: {_mask_secret(DB_PASSWORD)}")

    # Tenta conexão real para validar credenciais e rede local do MySQL.
    conn = None
    try:
        conn = mysql.connector.connect(**_db_config(com_database=True))
        print("Conexão MySQL: SUCESSO")
        return 0
    except mysql.connector.Error as exc:
        print("Conexão MySQL: FALHA")
        print(f"Erro MySQL: {exc}")
        return 1
    except Exception as exc:  # pylint: disable=broad-except
        print("Conexão MySQL: FALHA")
        print(f"Erro inesperado: {exc}")
        return 1
    finally:
        if conn is not None and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
