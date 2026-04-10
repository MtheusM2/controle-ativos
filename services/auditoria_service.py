"""
Serviço de auditoria para rastreabilidade de eventos críticos.

Cada operação importante do sistema registra um evento contendo:
- O quê foi feito (tipo de evento)
- Quem fez (usuario_id)
- Quando (timestamp)
- De onde (IP do cliente)
- Resultado (sucesso/falha)
- Detalhes (estado anterior/novo para edições)

Objetivo: conformidade LGPD, investigação de incidentes, homologação corporativa.
"""

from __future__ import annotations

import json
from datetime import datetime

from database.connection import cursor_mysql


class AuditoriaErro(Exception):
    """Erro base relacionado a auditoria."""

    pass


class TiposEvento:
    """Constantes de tipos de evento suportados."""

    # Eventos de Ativo
    ATIVO_CRIADO = "ATIVO_CRIADO"
    ATIVO_EDITADO = "ATIVO_EDITADO"
    ATIVO_REMOVIDO = "ATIVO_REMOVIDO"
    ATIVO_INATIVADO = "ATIVO_INATIVADO"

    # Eventos de Arquivo
    ARQUIVO_ENVIADO = "ARQUIVO_ENVIADO"
    ARQUIVO_REMOVIDO = "ARQUIVO_REMOVIDO"
    ARQUIVO_BAIXADO = "ARQUIVO_BAIXADO"

    # Eventos de Acesso
    LOGIN_SUCESSO = "LOGIN_SUCESSO"
    LOGIN_FALHA = "LOGIN_FALHA"
    LOGOUT = "LOGOUT"
    SESSAO_EXPIRADA = "SESSAO_EXPIRADA"

    # Eventos de Permissão
    ACESSO_NEGADO = "ACESSO_NEGADO"
    USUARIO_PROMOVIDO = "USUARIO_PROMOVIDO"
    USUARIO_BLOQUEADO = "USUARIO_BLOQUEADO"

    # Eventos de Exportação/Importação
    EXPORTACAO_REALIZADA = "EXPORTACAO_REALIZADA"
    IMPORTACAO_REALIZADA = "IMPORTACAO_REALIZADA"


class AuditoriaService:
    """
    Serviço responsável por registrar e consultar eventos de auditoria.

    Método estático para facilitar integração em qualquer parte do código.
    """

    @staticmethod
    def registrar_evento(
        tipo_evento: str,
        usuario_id: int | None,
        empresa_id: int,
        mensagem: str | None = None,
        dados_antes: dict | None = None,
        dados_depois: dict | None = None,
        ip_origem: str | None = None,
        user_agent: str | None = None,
        sucesso: bool = True,
        motivo_falha: str | None = None,
    ) -> int:
        """
        Registra um evento de auditoria no banco de dados.

        Args:
            tipo_evento: tipo do evento (constante de TiposEvento)
            usuario_id: ID do usuário que realizou ação (None se pré-autenticação)
            empresa_id: ID da empresa onde ocorreu o evento
            mensagem: descrição legível do que aconteceu
            dados_antes: estado anterior do recurso (para edições)
            dados_depois: estado novo do recurso (para edições)
            ip_origem: endereço IP do cliente
            user_agent: navegador/client info
            sucesso: True se operação bem-sucedida, False se falha
            motivo_falha: razão da falha (se sucesso=False)

        Returns:
            ID do evento registrado no banco

        Raises:
            AuditoriaErro: se ocorrer erro ao registrar
        """
        try:
            with cursor_mysql(dictionary=True) as (_conn, cur):
                cur.execute(
                    """
                    INSERT INTO auditoria_eventos (
                        tipo_evento,
                        usuario_id,
                        empresa_id,
                        ip_origem,
                        user_agent,
                        dados_antes,
                        dados_depois,
                        mensagem,
                        sucesso,
                        motivo_falha
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        tipo_evento,
                        usuario_id,
                        empresa_id,
                        ip_origem[:45] if ip_origem else None,  # Limita a tamanho de coluna
                        user_agent[:255] if user_agent else None,  # Limita a tamanho
                        json.dumps(dados_antes) if dados_antes else None,
                        json.dumps(dados_depois) if dados_depois else None,
                        mensagem[:1000] if mensagem else None,  # Limita tamanho de mensagem
                        1 if sucesso else 0,
                        motivo_falha[:255] if motivo_falha else None,
                    ),
                )

                return cur.lastrowid

        except Exception as e:
            raise AuditoriaErro(f"Falha ao registrar evento de auditoria: {e}")

    @staticmethod
    def listar_eventos(
        empresa_id: int,
        tipo_evento: str | None = None,
        usuario_id: int | None = None,
        limite: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        Lista eventos de auditoria com filtros opcionais.

        Nota: Esta operação deve ser protegida por validação de perfil (admin).

        Args:
            empresa_id: ID da empresa (filtro obrigatório)
            tipo_evento: tipo de evento (opcional)
            usuario_id: ID do usuário que realizou ação (opcional)
            limite: máximo de registros a retornar (padrão 100)
            offset: deslocamento para paginação

        Returns:
            Lista de dicionários com eventos
        """
        try:
            with cursor_mysql(dictionary=True) as (_conn, cur):
                # Monta cláusula WHERE dinamicamente
                where_clauses = ["empresa_id = %s"]
                params = [empresa_id]

                if tipo_evento:
                    where_clauses.append("tipo_evento = %s")
                    params.append(tipo_evento)

                if usuario_id is not None:
                    where_clauses.append("usuario_id = %s")
                    params.append(usuario_id)

                where_sql = " AND ".join(where_clauses)

                cur.execute(
                    f"""
                    SELECT
                        id,
                        tipo_evento,
                        usuario_id,
                        empresa_id,
                        ip_origem,
                        user_agent,
                        dados_antes,
                        dados_depois,
                        mensagem,
                        sucesso,
                        motivo_falha,
                        criado_em
                    FROM auditoria_eventos
                    WHERE {where_sql}
                    ORDER BY criado_em DESC
                    LIMIT %s OFFSET %s
                    """,
                    params + [limite, offset],
                )

                rows = cur.fetchall() or []

                # Converte JSON strings para dicts (segurança)
                for row in rows:
                    if row.get("dados_antes"):
                        try:
                            row["dados_antes"] = json.loads(row["dados_antes"])
                        except (json.JSONDecodeError, TypeError):
                            row["dados_antes"] = None

                    if row.get("dados_depois"):
                        try:
                            row["dados_depois"] = json.loads(row["dados_depois"])
                        except (json.JSONDecodeError, TypeError):
                            row["dados_depois"] = None

                return rows

        except Exception as e:
            raise AuditoriaErro(f"Falha ao listar eventos: {e}")

    @staticmethod
    def contar_eventos(
        empresa_id: int,
        tipo_evento: str | None = None,
        usuario_id: int | None = None,
    ) -> int:
        """
        Conta quantidade de eventos com filtros opcionais.

        Args:
            empresa_id: ID da empresa (filtro obrigatório)
            tipo_evento: tipo de evento (opcional)
            usuario_id: ID do usuário (opcional)

        Returns:
            Quantidade de eventos encontrados
        """
        try:
            with cursor_mysql(dictionary=True) as (_conn, cur):
                where_clauses = ["empresa_id = %s"]
                params = [empresa_id]

                if tipo_evento:
                    where_clauses.append("tipo_evento = %s")
                    params.append(tipo_evento)

                if usuario_id is not None:
                    where_clauses.append("usuario_id = %s")
                    params.append(usuario_id)

                where_sql = " AND ".join(where_clauses)

                cur.execute(
                    f"""
                    SELECT COUNT(*) as total
                    FROM auditoria_eventos
                    WHERE {where_sql}
                    """,
                    params,
                )

                row = cur.fetchone()
                return row.get("total") if row else 0

        except Exception as e:
            raise AuditoriaErro(f"Falha ao contar eventos: {e}")

    @staticmethod
    def obter_evento(evento_id: int) -> dict | None:
        """
        Obtém um evento específico pelo ID.

        Args:
            evento_id: ID do evento

        Returns:
            Dicionário com dados do evento, ou None se não encontrado
        """
        try:
            with cursor_mysql(dictionary=True) as (_conn, cur):
                cur.execute(
                    """
                    SELECT * FROM auditoria_eventos
                    WHERE id = %s
                    """,
                    (evento_id,),
                )

                row = cur.fetchone()

                if row and row.get("dados_antes"):
                    try:
                        row["dados_antes"] = json.loads(row["dados_antes"])
                    except (json.JSONDecodeError, TypeError):
                        row["dados_antes"] = None

                if row and row.get("dados_depois"):
                    try:
                        row["dados_depois"] = json.loads(row["dados_depois"])
                    except (json.JSONDecodeError, TypeError):
                        row["dados_depois"] = None

                return row

        except Exception as e:
            raise AuditoriaErro(f"Falha ao obter evento: {e}")
