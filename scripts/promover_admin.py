"""
Promove um usuário para perfil admin de forma auditada.

Uso:
    python scripts/promover_admin.py --email usuario@empresa.com
    python scripts/promover_admin.py --id 42

Requisitos:
    - Executado a partir da raiz do projeto (onde app.py está)
    - Acesso ao banco de dados (credenciais em .env)
    - confirmação explícita do operador
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import cursor_mysql  # noqa: E402

# Configura logging estruturado para auditoria
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ADMIN] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# Valor preferencial para perfil admin — "adm" é legado mas ainda aceito no sistema
PERFIL_ADMIN = "admin"


def buscar_usuario(cur, *, email=None, user_id=None) -> dict | None:
    """
    Busca um usuário por email ou ID e retorna seus dados junto com a empresa.
    """
    if email:
        cur.execute(
            "SELECT u.id, u.nome, u.email, u.perfil, e.nome AS empresa_nome "
            "FROM usuarios u JOIN empresas e ON e.id = u.empresa_id "
            "WHERE u.email = %s",
            (email,)
        )
    elif user_id:
        cur.execute(
            "SELECT u.id, u.nome, u.email, u.perfil, e.nome AS empresa_nome "
            "FROM usuarios u JOIN empresas e ON e.id = u.empresa_id "
            "WHERE u.id = %s",
            (user_id,)
        )
    else:
        return None

    return cur.fetchone()


def promover(email=None, user_id=None) -> int:
    """
    Promove um usuário para admin após confirmação do operador.
    Retorna 0 em sucesso, 1 em erro ou cancelamento.
    """
    with cursor_mysql(dictionary=True) as (conn, cur):
        usuario = buscar_usuario(cur, email=email, user_id=user_id)

        if usuario is None:
            log.error("Usuário não encontrado. Nenhuma alteração foi feita.")
            return 1

        perfil_atual = usuario["perfil"]

        # Verifica se o usuário já é admin
        if perfil_atual in {"adm", "admin"}:
            log.warning(
                "Usuário '%s' (id=%s) já é admin (perfil atual: '%s'). "
                "Nenhuma alteração necessária.",
                usuario["email"],
                usuario["id"],
                perfil_atual,
            )
            return 0

        # Exibe dados do usuário para confirmação
        print(f"\nUsuário encontrado:")
        print(f"  ID      : {usuario['id']}")
        print(f"  Nome    : {usuario['nome']}")
        print(f"  E-mail  : {usuario['email']}")
        print(f"  Perfil  : {perfil_atual}")
        print(f"  Empresa : {usuario['empresa_nome']}")
        print(f"\nNovo perfil: {PERFIL_ADMIN}")

        # Pede confirmação explícita do operador
        confirmacao = input("\nConfirmar promoção? [s/N] ").strip().lower()

        if confirmacao != "s":
            log.info("Operação cancelada pelo operador.")
            return 0

        # Altera o perfil no banco
        cur.execute(
            "UPDATE usuarios SET perfil = %s WHERE id = %s",
            (PERFIL_ADMIN, usuario["id"]),
        )
        # conn.commit() é chamado automaticamente pelo context manager

        # Loga a ação de forma auditada (timestamp UTC, dados relevantes)
        log.info(
            "PROMOVIDO: id=%s email='%s' perfil_anterior='%s' perfil_novo='%s' "
            "operado_em='%s'",
            usuario["id"],
            usuario["email"],
            perfil_atual,
            PERFIL_ADMIN,
            datetime.now(tz=timezone.utc).isoformat(),
        )

        print(
            f"\nUsuário '{usuario['email']}' promovido para '{PERFIL_ADMIN}' com sucesso."
        )
        return 0


def main() -> int:
    """
    Entry point do script.
    """
    parser = argparse.ArgumentParser(
        description="Promove usuário para perfil admin de forma auditada."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--email", help="E-mail do usuário a promover.")
    group.add_argument("--id", type=int, dest="user_id", help="ID do usuário a promover.")
    args = parser.parse_args()

    return promover(email=args.email, user_id=args.user_id)


if __name__ == "__main__":
    raise SystemExit(main())
