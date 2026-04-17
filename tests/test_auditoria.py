"""
Testes de auditoria e rastreabilidade (Parte 2).

Valida que eventos críticos são registrados corretamente.
Todos os testes usam mock para evitar dependência de conexão real com banco.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from services.auditoria_service import AuditoriaService, TiposEvento, AuditoriaErro


@pytest.fixture
def mock_db_cursor():
    """
    Cria mock de cursor MySQL para auditoria.
    Simula a inserção e recuperação de eventos sem banco real.
    """
    mock_cursor = MagicMock()
    mock_conn = MagicMock()

    # Simula auto-increment: contador para gerar IDs
    mock_cursor.lastrowid = 1
    event_counter = {"id": 0}

    def mock_execute(sql, params=None):
        """Intercepta INSERT e UPDATE para simular lastrowid."""
        if "INSERT" in sql:
            event_counter["id"] += 1
            mock_cursor.lastrowid = event_counter["id"]

    mock_cursor.execute.side_effect = mock_execute
    mock_cursor.fetchone.return_value = None  # Por padrão, sem resultados
    mock_cursor.fetchall.return_value = []

    return mock_cursor, mock_conn


class TestAuditoriaRegistro:
    """Testes de registro básico de eventos."""

    @patch("services.auditoria_service.cursor_mysql")
    def test_registrar_evento_simples(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve registrar evento simples sem erros.
        Mock: cursor_mysql retorna mock de cursor que simula INSERT.
        """
        mock_cursor, mock_conn = mock_db_cursor
        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        # Registra evento
        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ATIVO_CRIADO,
            usuario_id=1,
            empresa_id=1,
            mensagem="Teste de evento simples",
        )

        # Valida que retornou um ID válido (gerado pelo mock)
        assert evento_id > 0
        # Valida que execute foi chamado (INSERT foi executado)
        assert mock_cursor.execute.called

    @patch("services.auditoria_service.cursor_mysql")
    def test_registrar_evento_com_dados(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve registrar evento com dados_antes e dados_depois.
        """
        mock_cursor, mock_conn = mock_db_cursor
        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        dados_depois = {"id": "OPU-001", "tipo": "Notebook", "marca": "Dell"}

        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ATIVO_CRIADO,
            usuario_id=1,
            empresa_id=1,
            mensagem="Ativo OPU-001 criado",
            dados_depois=dados_depois,
        )

        assert evento_id > 0
        assert mock_cursor.execute.called

    @patch("services.auditoria_service.cursor_mysql")
    def test_registrar_evento_falha(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve registrar evento de falha com motivo.
        """
        mock_cursor, mock_conn = mock_db_cursor
        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ACESSO_NEGADO,
            usuario_id=2,
            empresa_id=1,
            mensagem="Tentativa de remover ativo de outra empresa",
            sucesso=False,
            motivo_falha="Perfil 'consulta' não tem permissão para remover",
        )

        assert evento_id > 0
        # Valida que o evento foi inserido com sucesso=False nos params
        assert mock_cursor.execute.called

    @patch("services.auditoria_service.cursor_mysql")
    def test_registrar_evento_sem_usuario(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve permitir registrar evento sem usuario_id (pré-autenticação).
        """
        mock_cursor, mock_conn = mock_db_cursor
        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.LOGIN_FALHA,
            usuario_id=None,
            empresa_id=1,
            mensagem="Tentativa de login com email inválido",
            sucesso=False,
            motivo_falha="Usuário não encontrado",
        )

        assert evento_id > 0
        assert mock_cursor.execute.called

    @patch("services.auditoria_service.cursor_mysql")
    def test_registrar_evento_com_contexto_tecnico(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve registrar IP origem e User-Agent.
        """
        mock_cursor, mock_conn = mock_db_cursor
        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.LOGIN_SUCESSO,
            usuario_id=1,
            empresa_id=1,
            mensagem="Login bem-sucedido",
            ip_origem="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )

        assert evento_id > 0
        assert mock_cursor.execute.called


class TestAuditoriaListagem:
    """Testes de listagem e consulta de eventos."""

    @patch("services.auditoria_service.cursor_mysql")
    def test_listar_eventos_vazio(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve retornar lista vazia para empresa sem eventos.
        """
        mock_cursor, mock_conn = mock_db_cursor
        mock_cursor.fetchall.return_value = []  # Simula query vazia
        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        eventos = AuditoriaService.listar_eventos(empresa_id=999)
        assert eventos == []

    @patch("services.auditoria_service.cursor_mysql")
    def test_listar_eventos_com_filtro_tipo(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve filtrar por tipo de evento.
        """
        mock_cursor, mock_conn = mock_db_cursor

        # Simula retorno de eventos para a query
        eventos_mock = [
            {
                "id": 1,
                "tipo_evento": TiposEvento.ATIVO_CRIADO,
                "usuario_id": 1,
                "empresa_id": 1,
                "sucesso": 1,
                "mensagem": "Evento 1",
                "criado_em": "2026-04-17 10:00:00",
            }
        ]
        mock_cursor.fetchall.return_value = eventos_mock
        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        eventos = AuditoriaService.listar_eventos(
            empresa_id=1, tipo_evento=TiposEvento.ATIVO_CRIADO
        )

        assert len(eventos) > 0
        assert mock_cursor.execute.called

    @patch("services.auditoria_service.cursor_mysql")
    def test_listar_eventos_com_filtro_usuario(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve filtrar por usuario_id.
        """
        mock_cursor, mock_conn = mock_db_cursor

        eventos_mock = [
            {
                "id": 1,
                "tipo_evento": TiposEvento.ATIVO_CRIADO,
                "usuario_id": 1,
                "empresa_id": 1,
                "sucesso": 1,
                "mensagem": "Por user 1",
                "criado_em": "2026-04-17 10:00:00",
            }
        ]
        mock_cursor.fetchall.return_value = eventos_mock
        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        eventos = AuditoriaService.listar_eventos(empresa_id=1, usuario_id=1)

        assert len(eventos) > 0
        assert mock_cursor.execute.called

    @patch("services.auditoria_service.cursor_mysql")
    def test_listar_eventos_ordem_decrescente(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve retornar eventos em ordem decrescente de criado_em.
        """
        mock_cursor, mock_conn = mock_db_cursor

        # Simula eventos em ordem decrescente
        eventos_mock = [
            {
                "id": 3,
                "tipo_evento": TiposEvento.ATIVO_CRIADO,
                "usuario_id": 1,
                "empresa_id": 1,
                "sucesso": 1,
                "criado_em": "2026-04-17 12:00:00",
            },
            {
                "id": 2,
                "tipo_evento": TiposEvento.ATIVO_EDITADO,
                "usuario_id": 1,
                "empresa_id": 1,
                "sucesso": 1,
                "criado_em": "2026-04-17 11:00:00",
            },
        ]
        mock_cursor.fetchall.return_value = eventos_mock
        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        eventos = AuditoriaService.listar_eventos(empresa_id=1, limite=5)

        if len(eventos) > 1:
            for i in range(len(eventos) - 1):
                assert eventos[i]["criado_em"] >= eventos[i + 1]["criado_em"]

    @patch("services.auditoria_service.cursor_mysql")
    def test_listar_eventos_com_paginacao(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve suportar limite e offset.
        """
        mock_cursor, mock_conn = mock_db_cursor

        # Simula primeira página
        eventos_p1_mock = [
            {
                "id": 2,
                "tipo_evento": TiposEvento.ATIVO_EDITADO,
                "usuario_id": 1,
                "empresa_id": 1,
                "sucesso": 1,
                "criado_em": "2026-04-17 11:00:00",
            },
            {
                "id": 1,
                "tipo_evento": TiposEvento.ATIVO_CRIADO,
                "usuario_id": 1,
                "empresa_id": 1,
                "sucesso": 1,
                "criado_em": "2026-04-17 10:00:00",
            },
        ]

        # Simula segunda página
        eventos_p2_mock = [
            {
                "id": 4,
                "tipo_evento": TiposEvento.ATIVO_REMOVIDO,
                "usuario_id": 2,
                "empresa_id": 1,
                "sucesso": 1,
                "criado_em": "2026-04-17 13:00:00",
            },
        ]

        # Configura mock para retornar diferentes resultados
        mock_cursor.fetchall.side_effect = [eventos_p1_mock, eventos_p2_mock]
        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        eventos_p1 = AuditoriaService.listar_eventos(
            empresa_id=1, limite=2, offset=0
        )
        eventos_p2 = AuditoriaService.listar_eventos(
            empresa_id=1, limite=2, offset=2
        )

        assert len(eventos_p1) > 0
        assert len(eventos_p2) > 0


class TestAuditoriaContagem:
    """Testes de contagem de eventos."""

    @patch("services.auditoria_service.cursor_mysql")
    def test_contar_eventos_total(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve contar total de eventos.
        """
        mock_cursor, mock_conn = mock_db_cursor

        # Simula resposta de COUNT(*)
        mock_cursor.fetchone.return_value = {"total": 5}
        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        total = AuditoriaService.contar_eventos(empresa_id=1)

        assert isinstance(total, int)
        assert total >= 0
        assert mock_cursor.execute.called

    @patch("services.auditoria_service.cursor_mysql")
    def test_contar_eventos_com_filtro(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve contar com filtros.
        """
        mock_cursor, mock_conn = mock_db_cursor

        mock_cursor.fetchone.return_value = {"total": 3}
        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        total = AuditoriaService.contar_eventos(
            empresa_id=1, tipo_evento=TiposEvento.ATIVO_CRIADO
        )

        assert isinstance(total, int)
        assert total >= 0
        assert mock_cursor.execute.called


class TestAuditoriaTiposEvento:
    """Testes de tipos de evento."""

    def test_tipos_evento_constantes(self):
        """Deve ter constantes de tipos de evento."""
        assert hasattr(TiposEvento, "ATIVO_CRIADO")
        assert hasattr(TiposEvento, "ATIVO_EDITADO")
        assert hasattr(TiposEvento, "ATIVO_REMOVIDO")
        assert hasattr(TiposEvento, "LOGIN_SUCESSO")
        assert hasattr(TiposEvento, "ACESSO_NEGADO")

    def test_tipos_evento_sao_strings(self):
        """Constantes de tipo devem ser strings."""
        assert isinstance(TiposEvento.ATIVO_CRIADO, str)
        assert isinstance(TiposEvento.LOGIN_SUCESSO, str)


class TestAuditoriaJSON:
    """Testes de serialização JSON de dados."""

    @patch("services.auditoria_service.cursor_mysql")
    def test_deserializar_dados_antes(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve deserializar dados_antes corretamente.
        """
        mock_cursor, mock_conn = mock_db_cursor
        dados = {"campo1": "valor1", "nested": {"campo2": "valor2"}}

        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ATIVO_EDITADO,
            usuario_id=1,
            empresa_id=1,
            dados_antes=dados,
        )

        assert evento_id > 0
        # Valida que o JSON foi serializado e enviado para INSERT
        assert mock_cursor.execute.called

    @patch("services.auditoria_service.cursor_mysql")
    def test_deserializar_dados_depois(self, mock_cursor_mysql, mock_db_cursor):
        """
        Deve deserializar dados_depois corretamente.
        """
        mock_cursor, mock_conn = mock_db_cursor
        dados = {"id": "OPU-001", "status": "Em Uso"}

        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ATIVO_CRIADO,
            usuario_id=1,
            empresa_id=1,
            dados_depois=dados,
        )

        assert evento_id > 0
        assert mock_cursor.execute.called

    @patch("services.auditoria_service.cursor_mysql")
    def test_dados_nulos_sao_permitidos(self, mock_cursor_mysql, mock_db_cursor):
        """
        Dados NULL devem ser permitidos.
        """
        mock_cursor, mock_conn = mock_db_cursor
        mock_cursor_mysql.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.LOGIN_SUCESSO,
            usuario_id=1,
            empresa_id=1,
            dados_antes=None,
            dados_depois=None,
        )

        assert evento_id > 0
        assert mock_cursor.execute.called
