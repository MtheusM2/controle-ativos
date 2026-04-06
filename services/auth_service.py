# services/auth_service.py

from __future__ import annotations

from datetime import datetime

from config import AUTH_LOCKOUT_MINUTES, AUTH_MAX_FAILED_ATTEMPTS
from database.connection import cursor_mysql
from models.usuario import Usuario
from utils.crypto import gerar_hash, normalizar_resposta_recuperacao, verificar_hash
from utils.validators import (
    validar_email,
    validar_id_inteiro_positivo,
    validar_perfil,
    validar_senha,
    validar_texto_obrigatorio,
)


class AuthErro(Exception):
    """
    Erro base de autenticacao.
    """


class UsuarioJaExiste(AuthErro):
    """
    Erro para usuario duplicado.
    """


class UsuarioNaoEncontrado(AuthErro):
    """
    Erro para usuario inexistente.
    """


class CredenciaisInvalidas(AuthErro):
    """
    Erro para login invalido.
    """


class RecuperacaoInvalida(AuthErro):
    """
    Erro para recuperacao invalida.
    """


class UsuarioBloqueado(AuthErro):
    """
    Erro para usuario temporariamente bloqueado por tentativas invalidas.
    """


def _normalizar_email(email: str) -> str:
    """
    Normaliza o e-mail para comparacao e armazenamento.
    """
    return (email or "").strip().lower()


def _agora_utc() -> datetime:
    """
    Retorna o horario atual em UTC para comparacoes locais.
    """
    return datetime.utcnow()


class AuthService:
    """
    Servico responsavel por cadastro, autenticacao e recuperacao de senha.
    """

    def _registrar_sucesso_login(self, cur, usuario_id: int) -> None:
        """
        Limpa contadores de falha e registra o ultimo login bem-sucedido.
        """
        cur.execute(
            """
            UPDATE usuarios
            SET ultimo_login_em = CURRENT_TIMESTAMP,
                tentativas_login_falhas = 0,
                bloqueado_ate = NULL
            WHERE id = %s
            """,
            (usuario_id,),
        )

    def _registrar_falha_login(self, cur, usuario_id: int, tentativas_atuais: int) -> bool:
        """
        Incrementa falhas de login e aplica bloqueio temporario quando necessario.
        """
        novas_tentativas = int(tentativas_atuais or 0) + 1

        if novas_tentativas >= AUTH_MAX_FAILED_ATTEMPTS:
            cur.execute(
                """
                UPDATE usuarios
                SET tentativas_login_falhas = %s,
                    bloqueado_ate = DATE_ADD(CURRENT_TIMESTAMP, INTERVAL %s MINUTE)
                WHERE id = %s
                """,
                (novas_tentativas, AUTH_LOCKOUT_MINUTES, usuario_id),
            )
            return True

        cur.execute(
            """
            UPDATE usuarios
            SET tentativas_login_falhas = %s
            WHERE id = %s
            """,
            (novas_tentativas, usuario_id),
        )
        return False

    def registrar_usuario(
        self,
        email: str,
        senha: str,
        pergunta: str,
        resposta: str,
        empresa_id,
        perfil: str = "usuario",
    ) -> int:
        """
        Registra um novo usuario vinculado a uma empresa ativa.
        """
        email_norm = _normalizar_email(email)
        perfil_norm = (perfil or "").strip().lower()

        if not validar_email(email_norm):
            raise AuthErro("E-mail invalido.")

        ok, msg = validar_senha(senha)
        if not ok:
            raise AuthErro(msg)

        ok, msg = validar_texto_obrigatorio(pergunta, "pergunta de recuperacao", 255)
        if not ok:
            raise AuthErro(msg)

        ok, msg = validar_texto_obrigatorio(resposta, "resposta de recuperacao", 255)
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
                (empresa_id_int,),
            )
            if cur.fetchone() is None:
                raise AuthErro("Empresa invalida ou inativa.")

            cur.execute("SELECT id FROM usuarios WHERE email = %s", (email_norm,))
            if cur.fetchone() is not None:
                raise UsuarioJaExiste("Ja existe um usuario cadastrado com este e-mail.")

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
                    empresa_id_int,
                ),
            )

            return int(cur.lastrowid)

    def autenticar(self, email: str, senha: str) -> Usuario:
        """
        Autentica o usuario e retorna o contexto completo de acesso.
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
                    u.tentativas_login_falhas,
                    u.bloqueado_ate,
                    e.nome AS empresa_nome
                FROM usuarios u
                INNER JOIN empresas e
                    ON e.id = u.empresa_id
                WHERE u.email = %s
                  AND e.ativa = 1
                """,
                (email_norm,),
            )
            row = cur.fetchone()

            if row is None:
                raise UsuarioNaoEncontrado("Usuario nao encontrado.")

            bloqueado_ate = row.get("bloqueado_ate")
            if bloqueado_ate is not None and bloqueado_ate > _agora_utc():
                raise UsuarioBloqueado(
                    "Usuario temporariamente bloqueado por excesso de tentativas invalidas."
                )

            if not verificar_hash(senha, row["senha_hash"]):
                bloqueado = self._registrar_falha_login(
                    cur,
                    usuario_id=int(row["id"]),
                    tentativas_atuais=int(row.get("tentativas_login_falhas") or 0),
                )
                if bloqueado:
                    raise UsuarioBloqueado(
                        "Usuario temporariamente bloqueado por excesso de tentativas invalidas."
                    )
                raise CredenciaisInvalidas("E-mail ou senha invalidos.")

            self._registrar_sucesso_login(cur, int(row["id"]))

        return Usuario(
            id=row["id"],
            email=row["email"],
            senha_hash=row["senha_hash"],
            pergunta_recuperacao=row["pergunta_recuperacao"],
            resposta_recuperacao_hash=row["resposta_recuperacao_hash"],
            perfil=row["perfil"],
            empresa_id=row["empresa_id"],
            empresa_nome=row["empresa_nome"],
        )

    def obter_pergunta_recuperacao(self, email: str) -> str:
        """
        Obtem a pergunta de recuperacao apenas de usuarios de empresas ativas.
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
                (email_norm,),
            )
            row = cur.fetchone()

        if row is None:
            raise UsuarioNaoEncontrado("Usuario nao encontrado.")

        return row["pergunta_recuperacao"]

    def redefinir_senha(self, email: str, resposta: str, nova_senha: str) -> None:
        """
        Redefine a senha apos validacao da resposta de recuperacao.
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
                (email_norm,),
            )
            row = cur.fetchone()

            if row is None:
                raise UsuarioNaoEncontrado("Usuario nao encontrado.")

            if not verificar_hash(
                normalizar_resposta_recuperacao(resposta),
                row["resposta_recuperacao_hash"],
            ):
                raise RecuperacaoInvalida("Resposta de recuperacao incorreta.")

            nova_hash = gerar_hash(nova_senha)

            cur.execute(
                """
                UPDATE usuarios
                SET senha_hash = %s,
                    senha_alterada_em = CURRENT_TIMESTAMP,
                    tentativas_login_falhas = 0,
                    bloqueado_ate = NULL,
                    reset_token_hash = NULL,
                    reset_token_expira_em = NULL,
                    reset_token_usado_em = NULL
                WHERE id = %s
                """,
                (nova_hash, row["id"]),
            )
