from models.ativos import Ativo
from database.connection import cursor_mysql
from utils.validators import STATUS_VALIDOS, validar_id_ativo, validar_status, padronizar_texto


class AtivoErro(Exception):
    pass


class AtivoJaExiste(AtivoErro):
    pass


class AtivoNaoEncontrado(AtivoErro):
    pass


class PermissaoNegada(AtivoErro):
    pass


def _padronizar_ativo(ativo: Ativo) -> Ativo:
    return Ativo(
        id_ativo=ativo.id_ativo.strip(),
        tipo=padronizar_texto(ativo.tipo, "title"),
        marca=padronizar_texto(ativo.marca, "title"),
        modelo=padronizar_texto(ativo.modelo, "upper"),
        usuario=padronizar_texto(ativo.usuario, "title"),
        departamento=padronizar_texto(ativo.departamento, "title"),
        status=padronizar_texto(ativo.status, "title"),
        criado_por=ativo.criado_por
    )


class AtivosService:
    def criar_ativo(self, ativo: Ativo, user_id: int) -> None:
        ok, msg = validar_id_ativo(ativo.id_ativo)
        if not ok:
            raise AtivoErro(msg)

        ok, msg = validar_status(ativo.status)
        if not ok:
            raise AtivoErro(msg)

        ativo_norm = _padronizar_ativo(ativo)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute("SELECT id FROM ativos WHERE id = %s", (ativo_norm.id_ativo,))
            if cur.fetchone() is not None:
                raise AtivoJaExiste("Já existe um ativo cadastrado com este ID.")

            cur.execute(
                """
                INSERT INTO ativos (id, tipo, marca, modelo, usuario, departamento, status, criado_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ativo_norm.id_ativo,
                    ativo_norm.tipo,
                    ativo_norm.marca,
                    ativo_norm.modelo,
                    ativo_norm.usuario,
                    ativo_norm.departamento,
                    ativo_norm.status,
                    user_id
                )
            )

    def listar_ativos(self, user_id: int) -> list[Ativo]:
        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                SELECT id, tipo, marca, modelo, usuario, departamento, status, criado_por
                FROM ativos
                WHERE criado_por = %s
                ORDER BY id
                """,
                (user_id,)
            )
            rows = cur.fetchall()

        return [
            Ativo(
                id_ativo=r["id"],
                tipo=r["tipo"],
                marca=r["marca"],
                modelo=r["modelo"],
                usuario=r["usuario"],
                departamento=r["departamento"],
                status=r["status"],
                criado_por=r["criado_por"]
            )
            for r in rows
        ]

    def buscar_ativo(self, id_ativo: str, user_id: int) -> Ativo:
        ok, msg = validar_id_ativo(id_ativo)
        if not ok:
            raise AtivoErro(msg)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                SELECT id, tipo, marca, modelo, usuario, departamento, status, criado_por
                FROM ativos
                WHERE id = %s
                """,
                (id_ativo.strip(),)
            )
            row = cur.fetchone()

        if row is None:
            raise AtivoNaoEncontrado("Ativo não encontrado.")

        if int(row["criado_por"]) != int(user_id):
            raise PermissaoNegada("Você não tem permissão para acessar este ativo.")

        return Ativo(
            id_ativo=row["id"],
            tipo=row["tipo"],
            marca=row["marca"],
            modelo=row["modelo"],
            usuario=row["usuario"],
            departamento=row["departamento"],
            status=row["status"],
            criado_por=row["criado_por"]
        )

    def atualizar_ativo(self, id_ativo: str, dados: dict, user_id: int) -> Ativo:
        atual = self.buscar_ativo(id_ativo=id_ativo, user_id=user_id)

        novo = Ativo(
            id_ativo=atual.id_ativo,
            tipo=dados.get("tipo", atual.tipo),
            marca=dados.get("marca", atual.marca),
            modelo=dados.get("modelo", atual.modelo),
            usuario=dados.get("usuario", atual.usuario),
            departamento=dados.get("departamento", atual.departamento),
            status=dados.get("status", atual.status),
            criado_por=atual.criado_por
        )

        ok, msg = validar_status(novo.status)
        if not ok:
            raise AtivoErro(msg)

        novo_norm = _padronizar_ativo(novo)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                UPDATE ativos
                SET tipo=%s, marca=%s, modelo=%s, usuario=%s, departamento=%s, status=%s
                WHERE id=%s AND criado_por=%s
                """,
                (
                    novo_norm.tipo,
                    novo_norm.marca,
                    novo_norm.modelo,
                    novo_norm.usuario,
                    novo_norm.departamento,
                    novo_norm.status,
                    novo_norm.id_ativo,
                    user_id
                )
            )

            if cur.rowcount == 0:
                raise AtivoNaoEncontrado("Não foi possível atualizar: ativo não encontrado ou sem permissão.")

        return novo_norm

    def remover_ativo(self, id_ativo: str, user_id: int) -> None:
        ok, msg = validar_id_ativo(id_ativo)
        if not ok:
            raise AtivoErro(msg)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                "DELETE FROM ativos WHERE id=%s AND criado_por=%s",
                (id_ativo.strip(), user_id)
            )

            if cur.rowcount == 0:
                raise AtivoNaoEncontrado("Não foi possível remover: ativo não encontrado ou sem permissão.")

    def status_disponiveis(self) -> list[str]:
        return list(STATUS_VALIDOS)