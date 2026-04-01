# services/auth_service.py

# Serviço responsável por:
# - cadastro de usuários
# - autenticação
# - recuperação de senha
# - validação do contexto organizacional do usuário

from models.usuario import Usuario
from database.connection import cursor_mysql
from utils.crypto import gerar_hash, verificar_hash, normalizar_resposta_recuperacao
from utils.validators import (
    validar_email,
    validar_senha,
    validar_texto_obrigatorio,
    validar_perfil,
    validar_id_inteiro_positivo
)


class AuthErro(Exception):
    """
    Erro base de autenticação.
    """
    pass


class UsuarioJaExiste(AuthErro):
    """
    Erro para usuário duplicado.
    """
    pass


class UsuarioNaoEncontrado(AuthErro):
    """
    Erro para usuário inexistente.
    """
    pass


class CredenciaisInvalidas(AuthErro):
    """
    Erro para login inválido.
    """
    pass


class RecuperacaoInvalida(AuthErro):
    """
    Erro para recuperação inválida.
    """
    pass


def _normalizar_email(email: str) -> str:
    """
    Normaliza o e-mail para comparação e armazenamento.
    """
    return (email or "").strip().lower()


class AuthService:
    """
    Serviço responsável por cadastro, autenticação e recuperação de senha.
    """

    def registrar_usuario(
        self,
        email: str,
        senha: str,
        pergunta: str,
        resposta: str,
        empresa_id,
        perfil: str = "usuario"
    ) -> int:
        """
        Registra um novo usuário vinculado a uma empresa.
        """
        email_norm = _normalizar_email(email)
        perfil_norm = (perfil or "").strip().lower()

        if not validar_email(email_norm):
            raise AuthErro("E-mail inválido.")

        ok, msg = validar_senha(senha)
        if not ok:
            raise AuthErro(msg)

        ok, msg = validar_texto_obrigatorio(pergunta, "pergunta de recuperação", 255)
        if not ok:
            raise AuthErro(msg)

        ok, msg = validar_texto_obrigatorio(resposta, "resposta de recuperação", 255)
        if not ok:
            raise AuthErro(msg)

        ok, msg = validar_perfil(perfil_norm)
        if not ok:
            raise AuthErro(msg)

        ok, msg = validar_id_inteiro_positivo(empresa_id, "empresa")
        if not ok:
            raise AuthErro(msg)

        empresa_id_int = int(empresa_id)

        senha_hash = gerar_hash(senha)
        resposta_hash = gerar_hash(normalizar_resposta_recuperacao(resposta))

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                SELECT id
                FROM empresas
                WHERE id = %s AND ativa = 1
                """,
                (empresa_id_int,)
            )
            empresa = cur.fetchone()

            if empresa is None:
                raise AuthErro("Empresa inválida ou inativa.")

            cur.execute(
                "SELECT id FROM usuarios WHERE email = %s",
                (email_norm,)
            )
            if cur.fetchone() is not None:
                raise UsuarioJaExiste("Já existe um usuário cadastrado com este e-mail.")

            cur.execute(
                """
                INSERT INTO usuarios (
                    email,
                    senha_hash,
                    pergunta_recuperacao,
                    resposta_recuperacao_hash,
                    perfil,
                    empresa_id
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    email_norm,
                    senha_hash,
                    pergunta.strip(),
                    resposta_hash,
                    perfil_norm,
                    empresa_id_int
                )
            )

            return int(cur.lastrowid)

    def autenticar(self, email: str, senha: str) -> Usuario:
        """
        Autentica o usuário e retorna o contexto completo de acesso.
        Também atualiza o timestamp do último login bem-sucedido.
        """
        email_norm = _normalizar_email(email)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                SELECT
                    u.id,
                    u.email,
                    u.senha_hash,
                    u.pergunta_recuperacao,
                    u.resposta_recuperacao_hash,
                    u.perfil,
                    u.empresa_id,
                    e.nome AS empresa_nome
                FROM usuarios u
                INNER JOIN empresas e
                    ON e.id = u.empresa_id
                WHERE u.email = %s
                  AND e.ativa = 1
                """,
                (email_norm,)
            )
            row = cur.fetchone()

            if row is None:
                raise UsuarioNaoEncontrado("Usuário não encontrado.")

            if not verificar_hash(senha, row["senha_hash"]):
                raise CredenciaisInvalidas("E-mail ou senha inválidos.")

            cur.execute(
                """
                UPDATE usuarios
                SET ultimo_login_em = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (row["id"],)
            )

        return Usuario(
            id=row["id"],
            email=row["email"],
            senha_hash=row["senha_hash"],
            pergunta_recuperacao=row["pergunta_recuperacao"],
            resposta_recuperacao_hash=row["resposta_recuperacao_hash"],
            perfil=row["perfil"],
            empresa_id=row["empresa_id"],
            empresa_nome=row["empresa_nome"]
        )

    def obter_pergunta_recuperacao(self, email: str) -> str:
        """
        Obtém a pergunta de recuperação apenas de usuários
        vinculados a empresas ativas.
        """
        email_norm = _normalizar_email(email)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                SELECT u.pergunta_recuperacao
                FROM usuarios u
                INNER JOIN empresas e
                    ON e.id = u.empresa_id
                WHERE u.email = %s
                  AND e.ativa = 1
                """,
                (email_norm,)
            )
            row = cur.fetchone()

        if row is None:
            raise UsuarioNaoEncontrado("Usuário não encontrado.")

        return row["pergunta_recuperacao"]

    def redefinir_senha(self, email: str, resposta: str, nova_senha: str) -> None:
        """
        Redefine a senha após validação da resposta de recuperação,
        considerando apenas usuários de empresas ativas.
        """
        email_norm = _normalizar_email(email)

        ok, msg = validar_senha(nova_senha)
        if not ok:
            raise AuthErro(msg)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                SELECT u.id, u.resposta_recuperacao_hash
                FROM usuarios u
                INNER JOIN empresas e
                    ON e.id = u.empresa_id
                WHERE u.email = %s
                  AND e.ativa = 1
                """,
                (email_norm,)
            )
            row = cur.fetchone()

            if row is None:
                raise UsuarioNaoEncontrado("Usuário não encontrado.")

            if not verificar_hash(
                normalizar_resposta_recuperacao(resposta),
                row["resposta_recuperacao_hash"]
            ):
                raise RecuperacaoInvalida("Resposta de recuperação incorreta.")

            nova_hash = gerar_hash(nova_senha)

            cur.execute(
                """
                UPDATE usuarios
                SET senha_hash = %s,
                    senha_alterada_em = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (nova_hash, row["id"])
            )