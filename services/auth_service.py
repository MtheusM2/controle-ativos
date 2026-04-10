# services/auth_service.py

from __future__ import annotations

import threading
from datetime import datetime
from typing import Iterable

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


class PermissaoAuthNegada(AuthErro):
    """
    Erro para tentativas de alteracao fora da permissao do perfil.
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


def _agora_local() -> datetime:
    """
    Retorna o horario local do servidor para comparacao com valores gravados pelo MySQL.
    O CURRENT_TIMESTAMP do MySQL grava a hora local do servidor (nao UTC).
    Em producao Windows Server (fuso America/Sao_Paulo), ambos devem estar sincronizados.
    """
    return datetime.now()


def _nome_padrao_por_email(email: str) -> str:
    """
    Gera um nome inicial amigavel quando o usuario nao possui nome explicito.
    """
    local = (email or "").split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
    return (local or "Usuario").title()


class AuthService:
    """
    Servico responsavel por cadastro, autenticacao e recuperacao de senha.
    """

    def __init__(self) -> None:
        # Cacheia colunas da tabela usuarios para reduzir custo em consultas repetidas.
        self._usuarios_columns_cache: set[str] | None = None
        # Lock para garantir que apenas uma thread inicializa o cache simultaneamente.
        self._cache_lock = threading.Lock()

    def _carregar_colunas_usuarios(self, cur) -> set[str]:
        """
        Le colunas reais de usuarios no banco atual para suportar evolucao por migration.
        """
        cur.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'usuarios'
            """
        )
        rows = cur.fetchall() or []
        colunas = {
            (row.get("COLUMN_NAME") if isinstance(row, dict) else row[0])
            for row in rows
        }
        self._usuarios_columns_cache = {str(coluna) for coluna in colunas if coluna}
        return self._usuarios_columns_cache

    def _usuarios_tem_colunas(self, cur, nomes: Iterable[str]) -> bool:
        """
        Verifica de forma retrocompativel se todas as colunas exigidas ja existem no schema.
        Protegido por lock para evitar condicao de corrida na inicializacao em ambiente multi-thread.
        """
        if self._usuarios_columns_cache is None:
            with self._cache_lock:
                # Verificacao dupla: outra thread pode ter inicializado enquanto aguardava o lock.
                if self._usuarios_columns_cache is None:
                    self._carregar_colunas_usuarios(cur)

        return all(nome in (self._usuarios_columns_cache or set()) for nome in nomes)

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
        nome: str | None = None,
    ) -> int:
        """
        Registra um novo usuario vinculado a uma empresa ativa.
        """
        email_norm = _normalizar_email(email)
        perfil_norm = (perfil or "").strip().lower()
        nome_norm = (nome or "").strip() or _nome_padrao_por_email(email_norm)

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

        ok, msg = validar_texto_obrigatorio(nome_norm, "nome", 120)
        if not ok:
            raise AuthErro(msg)

        ok, msg = validar_id_inteiro_positivo(empresa_id, "empresa")
        if not ok:
            raise AuthErro(msg)

        empresa_id_int = int(empresa_id)
        senha_hash = gerar_hash(senha)
        resposta_hash = gerar_hash(normalizar_resposta_recuperacao(resposta))

        with cursor_mysql(dictionary=True) as (_conn, cur):
            tem_coluna_nome = self._usuarios_tem_colunas(cur, {"nome"})

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

            if tem_coluna_nome:
                cur.execute(
                    """
                    INSERT INTO usuarios (
                        nome,
                        email,
                        senha_hash,
                        pergunta_recuperacao,
                        resposta_recuperacao_hash,
                        perfil,
                        empresa_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        nome_norm,
                        email_norm,
                        senha_hash,
                        pergunta.strip(),
                        resposta_hash,
                        perfil_norm,
                        empresa_id_int,
                    ),
                )
            else:
                # Compatibilidade: em bases antigas sem migration 004, persiste sem nome.
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
            tem_coluna_nome = self._usuarios_tem_colunas(cur, {"nome"})
            tem_coluna_lembrar = self._usuarios_tem_colunas(cur, {"lembrar_me_ativo"})

            select_colunas = [
                "u.id",
                "u.email",
                "u.senha_hash",
                "u.pergunta_recuperacao",
                "u.resposta_recuperacao_hash",
                "u.perfil",
                "u.empresa_id",
                "u.tentativas_login_falhas",
                "u.bloqueado_ate",
                "e.nome AS empresa_nome",
            ]

            if tem_coluna_nome:
                select_colunas.insert(1, "u.nome")

            if tem_coluna_lembrar:
                select_colunas.insert(8, "u.lembrar_me_ativo")

            cur.execute(
                f"""
                SELECT
                    {", ".join(select_colunas)}
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
            if bloqueado_ate is not None and bloqueado_ate > _agora_local():
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
            nome=row.get("nome") or _nome_padrao_por_email(row["email"]),
            email=row["email"],
            senha_hash=row["senha_hash"],
            pergunta_recuperacao=row["pergunta_recuperacao"],
            resposta_recuperacao_hash=row["resposta_recuperacao_hash"],
            perfil=row["perfil"],
            empresa_id=row["empresa_id"],
            empresa_nome=row["empresa_nome"],
            lembrar_me_ativo=bool(row.get("lembrar_me_ativo")),
        )

    def obter_usuario_por_id(self, user_id: int) -> dict:
        """
        Retorna dados essenciais do usuario logado para tela de configuracoes.
        """
        with cursor_mysql(dictionary=True) as (_conn, cur):
            tem_coluna_nome = self._usuarios_tem_colunas(cur, {"nome"})
            tem_coluna_lembrar = self._usuarios_tem_colunas(cur, {"lembrar_me_ativo"})

            select_colunas = [
                "u.id",
                "u.email",
                "u.perfil",
                "u.empresa_id",
                "e.nome AS empresa_nome",
            ]

            if tem_coluna_nome:
                select_colunas.insert(1, "u.nome")

            if tem_coluna_lembrar:
                select_colunas.insert(4, "u.lembrar_me_ativo")

            cur.execute(
                f"""
                SELECT
                    {", ".join(select_colunas)}
                FROM usuarios u
                INNER JOIN empresas e
                    ON e.id = u.empresa_id
                WHERE u.id = %s
                  AND e.ativa = 1
                """,
                (user_id,),
            )
            row = cur.fetchone()

        if row is None:
            raise UsuarioNaoEncontrado("Usuario nao encontrado.")

        row["nome"] = (row.get("nome") or "").strip() or _nome_padrao_por_email(row.get("email") or "")
        row["lembrar_me_ativo"] = bool(row.get("lembrar_me_ativo"))
        row["suporta_nome"] = bool(tem_coluna_nome)
        row["suporta_lembrar_me"] = bool(tem_coluna_lembrar)
        return row

    def atualizar_preferencia_lembrar_me(self, user_id: int, ativo: bool) -> None:
        """
        Atualiza a preferencia persistente de sessao prolongada do usuario.
        """
        with cursor_mysql(dictionary=True) as (_conn, cur):
            if not self._usuarios_tem_colunas(cur, {"lembrar_me_ativo"}):
                raise AuthErro(
                    "A preferencia 'lembrar de mim' requer atualizacao de banco (migration 004)."
                )

            cur.execute(
                """
                UPDATE usuarios
                SET lembrar_me_ativo = %s
                WHERE id = %s
                """,
                (1 if ativo else 0, user_id),
            )

            if cur.rowcount == 0:
                raise UsuarioNaoEncontrado("Usuario nao encontrado.")

    def atualizar_proprio_perfil(self, user_id: int, nome: str, email: str | None = None) -> dict:
        """
        Atualiza nome (todos) e e-mail (somente admin) do proprio usuario.
        """
        contexto = self.obter_usuario_por_id(user_id)
        nome_norm = (nome or "").strip()

        ok, msg = validar_texto_obrigatorio(nome_norm, "nome", 120)
        if not ok:
            raise AuthErro(msg)

        perfil = (contexto.get("perfil") or "").strip().lower()
        admin = perfil in {"adm", "admin"}

        email_atual = contexto["email"]
        email_norm = _normalizar_email(email or email_atual)

        if email_norm != email_atual and not admin:
            raise PermissaoAuthNegada("Apenas administradores podem alterar o e-mail.")

        if email_norm != email_atual and not validar_email(email_norm):
            raise AuthErro("E-mail invalido.")

        with cursor_mysql(dictionary=True) as (_conn, cur):
            tem_coluna_nome = self._usuarios_tem_colunas(cur, {"nome"})

            if email_norm != email_atual:
                cur.execute(
                    "SELECT id FROM usuarios WHERE email = %s AND id <> %s",
                    (email_norm, user_id),
                )
                if cur.fetchone() is not None:
                    raise UsuarioJaExiste("Ja existe um usuario cadastrado com este e-mail.")

            if tem_coluna_nome:
                cur.execute(
                    """
                    UPDATE usuarios
                    SET nome = %s,
                        email = %s
                    WHERE id = %s
                    """,
                    (nome_norm, email_norm, user_id),
                )
            else:
                nome_exibicao_atual = contexto.get("nome") or _nome_padrao_por_email(email_atual)
                if nome_norm != nome_exibicao_atual:
                    raise AuthErro(
                        "Alteracao de nome requer atualizacao de banco (migration 004)."
                    )

                # Compatibilidade: em bases antigas so permite update de e-mail (admin).
                cur.execute(
                    """
                    UPDATE usuarios
                    SET email = %s
                    WHERE id = %s
                    """,
                    (email_norm, user_id),
                )

            if cur.rowcount == 0:
                raise UsuarioNaoEncontrado("Usuario nao encontrado.")

        return self.obter_usuario_por_id(user_id)

    def alterar_senha_propria(self, user_id: int, senha_atual: str, nova_senha: str) -> None:
        """
        Atualiza a senha do proprio usuario validando a senha atual.
        """
        ok, msg = validar_senha(nova_senha)
        if not ok:
            raise AuthErro(msg)

        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                "SELECT id, senha_hash FROM usuarios WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()

            if row is None:
                raise UsuarioNaoEncontrado("Usuario nao encontrado.")

            if not verificar_hash(senha_atual or "", row["senha_hash"]):
                raise CredenciaisInvalidas("Senha atual invalida.")

            nova_hash = gerar_hash(nova_senha)
            cur.execute(
                """
                UPDATE usuarios
                SET senha_hash = %s,
                    senha_alterada_em = CURRENT_TIMESTAMP,
                    tentativas_login_falhas = 0,
                    bloqueado_ate = NULL
                WHERE id = %s
                """,
                (nova_hash, user_id),
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

    # ================================================================
    # METODOS DE PERMISSAO (PARTE 2)
    # Fonte centralizada de verdade para decisões de autorização
    # ================================================================

    def eh_admin(self, perfil: str | None) -> bool:
        """
        Verifica se o perfil é de administrador.
        Normaliza 'adm' e 'admin' para tratamento unificado.
        """
        perfil_norm = (perfil or "").strip().lower()
        return perfil_norm in {"admin", "adm"}

    def normalizar_perfil(self, perfil: str | None) -> str:
        """
        Normaliza um perfil para um valor canônico.
        Parte 1 usava 'usuario'; Parte 2 mapeia como 'operador'.
        """
        perfil_norm = (perfil or "").strip().lower()

        # Mapeamento de compatibilidade
        if perfil_norm == "usuario":
            return "operador"
        if perfil_norm == "adm":
            return "admin"

        # Validar que é um perfil conhecido
        if perfil_norm in {"admin", "gestor_unidade", "operador", "consulta"}:
            return perfil_norm

        # Padrão seguro (nunca deveria chegar aqui)
        return "operador"

    def obter_contexto_permissao(
        self, user_id: int, empresa_id: int, perfil: str
    ):
        """
        Cria um contexto de permissões para validações.
        Retorna objeto Usuario (de utils.permissions) com métodos de check.

        Uso na service:
            ctx = auth_service.obter_contexto_permissao(user_id, empresa_id, perfil)
            if not ctx.pode_criar_ativo(ativo_empresa_id):
                raise PermissaoNegada("...")
        """
        from utils.permissions import Usuario

        return Usuario(id=user_id, empresa_id=empresa_id, perfil=perfil)
