from models.usuario import Usuario
from database.connection import cursor_mysql
from utils.crypto import gerar_hash, verificar_hash, normalizar_resposta_recuperacao
from utils.validators import validar_email, validar_senha


class AuthErro(Exception):
    pass


class UsuarioJaExiste(AuthErro):
    pass


class UsuarioNaoEncontrado(AuthErro):
    pass


class CredenciaisInvalidas(AuthErro):
    pass


class RecuperacaoInvalida(AuthErro):
    pass


def _normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


class AuthService:
    def registrar_usuario(self, email: str, senha: str, pergunta: str, resposta: str) -> int:
        email_norm = _normalizar_email(email)

        if not validar_email(email_norm):
            raise AuthErro("E-mail inválido.")

        ok, msg = validar_senha(senha)
        if not ok:
            raise AuthErro(msg)

        if not (pergunta or "").strip():
            raise AuthErro("A pergunta de recuperação não pode ficar vazia.")

        if not (resposta or "").strip():
            raise AuthErro("A resposta de recuperação não pode ficar vazia.")

        senha_hash = gerar_hash(senha)
        resposta_norm = normalizar_resposta_recuperacao(resposta)
        resposta_hash = gerar_hash(resposta_norm)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (email_norm,))
            if cur.fetchone() is not None:
                raise UsuarioJaExiste("Já existe um usuário cadastrado com este e-mail.")

            cur.execute(
                """
                INSERT INTO usuarios (email, senha_hash, pergunta_recuperacao, resposta_recuperacao_hash)
                VALUES (%s, %s, %s, %s)
                """,
                (email_norm, senha_hash, pergunta.strip(), resposta_hash)
            )

            return int(cur.lastrowid)

    def autenticar(self, email: str, senha: str) -> Usuario:
        email_norm = _normalizar_email(email)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                SELECT id, email, senha_hash, pergunta_recuperacao, resposta_recuperacao_hash
                FROM usuarios
                WHERE email = %s
                """,
                (email_norm,)
            )
            row = cur.fetchone()

        if row is None:
            raise UsuarioNaoEncontrado("Usuário não encontrado.")

        if not verificar_hash(senha, row["senha_hash"]):
            raise CredenciaisInvalidas("E-mail ou senha inválidos.")

        return Usuario(
            id=row["id"],
            email=row["email"],
            senha_hash=row["senha_hash"],
            pergunta_recuperacao=row["pergunta_recuperacao"],
            resposta_recuperacao_hash=row["resposta_recuperacao_hash"]
        )

    def obter_pergunta_recuperacao(self, email: str) -> str:
        email_norm = _normalizar_email(email)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                "SELECT pergunta_recuperacao FROM usuarios WHERE email = %s",
                (email_norm,)
            )
            row = cur.fetchone()

        if row is None:
            raise UsuarioNaoEncontrado("Usuário não encontrado.")

        return row["pergunta_recuperacao"]

    def redefinir_senha(self, email: str, resposta: str, nova_senha: str) -> None:
        email_norm = _normalizar_email(email)

        ok, msg = validar_senha(nova_senha)
        if not ok:
            raise AuthErro(msg)

        resposta_norm = normalizar_resposta_recuperacao(resposta)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                "SELECT id, resposta_recuperacao_hash FROM usuarios WHERE email = %s",
                (email_norm,)
            )
            row = cur.fetchone()

            if row is None:
                raise UsuarioNaoEncontrado("Usuário não encontrado.")

            if not verificar_hash(resposta_norm, row["resposta_recuperacao_hash"]):
                raise RecuperacaoInvalida("Resposta de recuperação incorreta.")

            nova_hash = gerar_hash(nova_senha)

            cur.execute(
                "UPDATE usuarios SET senha_hash = %s WHERE id = %s",
                (nova_hash, row["id"])
            )