"""
check_db_connection_safe.py

Script de uso no servidor para checar a conectividade MySQL de forma segura.
- Usa a mesma configuração da aplicação (via database.connection).
- Não imprime nem grava senhas.
- Tradução de erros em categorias seguras para ajudar o diagnóstico.

Uso (no servidor):
python scripts/check_db_connection_safe.py

Retornos:
 - código 0: conexão bem-sucedida
 - código 1: falha na conexão (mensagem segura impressa)

Este arquivo NÃO deve conter senhas e pode ser mantido no repositório.
"""

from __future__ import annotations

import sys
from pathlib import Path

import mysql.connector
from mysql.connector import errorcode

# Garante import dos módulos do projeto ao executar via "python scripts/...".
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import _db_config  # noqa: E402


def main() -> int:
    """Tenta conectar e retorna diagnóstico seguro."""
    try:
        cfg = _db_config(com_database=True)

        # Não imprimir cfg para evitar exposição de segredos
        conn = mysql.connector.connect(**cfg)
        cur = conn.cursor()
        cur.execute("SELECT CURRENT_USER(), DATABASE();")
        user, db = cur.fetchone()
        print("Conexão com banco: SUCESSO")
        print(f"Usuário conectado: {user}")
        print(f"Banco selecionado: {db}")
        cur.close()
        conn.close()
        return 0

    except mysql.connector.Error as exc:
        # Mapeia erros comuns para mensagens seguras sem vazar segredos
        code = getattr(exc, 'errno', None)

        if code == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Falha: Autenticação falhou (usuário/senha inválidos ou usuário sem permissão).")
        elif code == errorcode.ER_BAD_DB_ERROR:
            print("Falha: Banco de dados não encontrado (DB_NAME incorreto ou banco não existe).")
        elif code in (errorcode.CR_CONN_HOST_ERROR, errorcode.ER_HOST_NOT_PRIVILEGED):
            print("Falha: Não foi possível alcançar o servidor MySQL (host/porta incorretos ou rede).")
        else:
            # Mensagem genérica; pode ser usada para referência ao DBA.
            print("Falha: erro de conexão com o MySQL. Consulte o administrador para detalhes.")

        return 1

    except Exception:
        print("Falha: erro inesperado ao testar a conexão. Verifique logs do sistema.")
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
