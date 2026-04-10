"""
Testes de auditoria e rastreabilidade (Parte 2).

Valida que eventos críticos são registrados corretamente.
"""

import pytest
import json
from services.auditoria_service import AuditoriaService, TiposEvento, AuditoriaErro


class TestAuditoriaRegistro:
    """Testes de registro básico de eventos."""

    def test_registrar_evento_simples(self):
        """Deve registrar evento simples sem erros."""
        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ATIVO_CRIADO,
            usuario_id=1,
            empresa_id=1,
            mensagem="Teste de evento simples",
        )

        assert evento_id > 0

        # Verifica que foi registrado
        evento = AuditoriaService.obter_evento(evento_id)
        assert evento is not None
        assert evento["tipo_evento"] == TiposEvento.ATIVO_CRIADO
        assert evento["usuario_id"] == 1
        assert evento["empresa_id"] == 1
        assert evento["sucesso"] == 1

    def test_registrar_evento_com_dados(self):
        """Deve registrar evento com dados_antes e dados_depois."""
        dados_depois = {"id": "OPU-001", "tipo": "Notebook", "marca": "Dell"}

        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ATIVO_CRIADO,
            usuario_id=1,
            empresa_id=1,
            mensagem="Ativo OPU-001 criado",
            dados_depois=dados_depois,
        )

        evento = AuditoriaService.obter_evento(evento_id)
        assert evento["dados_depois"] == dados_depois

    def test_registrar_evento_falha(self):
        """Deve registrar evento de falha com motivo."""
        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ACESSO_NEGADO,
            usuario_id=2,
            empresa_id=1,
            mensagem="Tentativa de remover ativo de outra empresa",
            sucesso=False,
            motivo_falha="Perfil 'consulta' não tem permissão para remover",
        )

        evento = AuditoriaService.obter_evento(evento_id)
        assert evento["sucesso"] == 0
        assert evento["motivo_falha"] == "Perfil 'consulta' não tem permissão para remover"

    def test_registrar_evento_sem_usuario(self):
        """Deve permitir registrar evento sem usuario_id (pré-autenticação)."""
        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.LOGIN_FALHA,
            usuario_id=None,
            empresa_id=1,
            mensagem="Tentativa de login com email inválido",
            sucesso=False,
            motivo_falha="Usuário não encontrado",
        )

        evento = AuditoriaService.obter_evento(evento_id)
        assert evento["usuario_id"] is None
        assert evento["sucesso"] == 0

    def test_registrar_evento_com_contexto_tecnico(self):
        """Deve registrar IP origem e User-Agent."""
        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.LOGIN_SUCESSO,
            usuario_id=1,
            empresa_id=1,
            mensagem="Login bem-sucedido",
            ip_origem="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )

        evento = AuditoriaService.obter_evento(evento_id)
        assert evento["ip_origem"] == "192.168.1.100"
        assert "Mozilla" in evento["user_agent"]


class TestAuditoriaListagem:
    """Testes de listagem e consulta de eventos."""

    def test_listar_eventos_vazio(self):
        """Deve retornar lista vazia para empresa sem eventos."""
        # Usa empresa_id 999 que provavelmente não tem eventos
        eventos = AuditoriaService.listar_eventos(empresa_id=999)
        assert eventos == []

    def test_listar_eventos_com_filtro_tipo(self):
        """Deve filtrar por tipo de evento."""
        # Registra dois eventos diferentes
        AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ATIVO_CRIADO,
            usuario_id=1,
            empresa_id=1,
            mensagem="Evento 1",
        )

        AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ATIVO_REMOVIDO,
            usuario_id=1,
            empresa_id=1,
            mensagem="Evento 2",
        )

        # Filtra por tipo
        eventos = AuditoriaService.listar_eventos(
            empresa_id=1, tipo_evento=TiposEvento.ATIVO_CRIADO
        )

        assert len(eventos) > 0
        assert all(e["tipo_evento"] == TiposEvento.ATIVO_CRIADO for e in eventos)

    def test_listar_eventos_com_filtro_usuario(self):
        """Deve filtrar por usuario_id."""
        AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ATIVO_CRIADO,
            usuario_id=1,
            empresa_id=1,
            mensagem="Por user 1",
        )

        AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ATIVO_CRIADO,
            usuario_id=2,
            empresa_id=1,
            mensagem="Por user 2",
        )

        eventos = AuditoriaService.listar_eventos(empresa_id=1, usuario_id=1)

        assert len(eventos) > 0
        assert all(e["usuario_id"] == 1 for e in eventos)

    def test_listar_eventos_ordem_decrescente(self):
        """Deve retornar eventos em ordem decrescente de criado_em."""
        eventos = AuditoriaService.listar_eventos(empresa_id=1, limite=5)

        if len(eventos) > 1:
            for i in range(len(eventos) - 1):
                assert eventos[i]["criado_em"] >= eventos[i + 1]["criado_em"]

    def test_listar_eventos_com_paginacao(self):
        """Deve suportar limite e offset."""
        eventos_p1 = AuditoriaService.listar_eventos(
            empresa_id=1, limite=2, offset=0
        )
        eventos_p2 = AuditoriaService.listar_eventos(
            empresa_id=1, limite=2, offset=2
        )

        # Não devem ser os mesmos
        if len(eventos_p1) > 0 and len(eventos_p2) > 0:
            assert eventos_p1[0]["id"] != eventos_p2[0]["id"]


class TestAuditoriaContagem:
    """Testes de contagem de eventos."""

    def test_contar_eventos_total(self):
        """Deve contar total de eventos."""
        total_inicial = AuditoriaService.contar_eventos(empresa_id=1)

        AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ATIVO_CRIADO,
            usuario_id=1,
            empresa_id=1,
            mensagem="Teste de contagem",
        )

        total_final = AuditoriaService.contar_eventos(empresa_id=1)
        assert total_final > total_inicial

    def test_contar_eventos_com_filtro(self):
        """Deve contar com filtros."""
        total = AuditoriaService.contar_eventos(
            empresa_id=1, tipo_evento=TiposEvento.ATIVO_CRIADO
        )

        assert isinstance(total, int)
        assert total >= 0


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

    def test_deserializar_dados_antes(self):
        """Deve deserializar dados_antes corretamente."""
        dados = {"campo1": "valor1", "nested": {"campo2": "valor2"}}

        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ATIVO_EDITADO,
            usuario_id=1,
            empresa_id=1,
            dados_antes=dados,
        )

        evento = AuditoriaService.obter_evento(evento_id)
        assert evento["dados_antes"] == dados

    def test_deserializar_dados_depois(self):
        """Deve deserializar dados_depois corretamente."""
        dados = {"id": "OPU-001", "status": "Em Uso"}

        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.ATIVO_CRIADO,
            usuario_id=1,
            empresa_id=1,
            dados_depois=dados,
        )

        evento = AuditoriaService.obter_evento(evento_id)
        assert evento["dados_depois"] == dados

    def test_dados_nulos_sao_permitidos(self):
        """Dados NULL devem ser permitidos."""
        evento_id = AuditoriaService.registrar_evento(
            tipo_evento=TiposEvento.LOGIN_SUCESSO,
            usuario_id=1,
            empresa_id=1,
            dados_antes=None,
            dados_depois=None,
        )

        evento = AuditoriaService.obter_evento(evento_id)
        assert evento["dados_antes"] is None
        assert evento["dados_depois"] is None
