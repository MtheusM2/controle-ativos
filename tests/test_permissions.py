"""
Testes de permissões e controle de acesso (Parte 2).

Valida que cada perfil tem acesso às ações corretas.
"""

import pytest
from utils.permissions import Usuario, criar_usuario_contexto


class TestPermissionsBasico:
    """Testes básicos de permissão de perfis."""

    def test_admin_eh_admin(self):
        """Admin deve ser identificado como admin."""
        user = Usuario(id=1, empresa_id=1, perfil="admin")
        assert user.eh_admin() is True

    def test_admin_normalizado(self):
        """'adm' deve ser normalizado para 'admin'."""
        user = Usuario(id=1, empresa_id=1, perfil="adm")
        assert user.normalizar_perfil() == "admin"

    def test_usuario_mapeado_para_operador(self):
        """'usuario' (Parte 1) deve ser mapeado como 'operador'."""
        user = Usuario(id=1, empresa_id=1, perfil="usuario")
        assert user.normalizar_perfil() == "operador"

    def test_gestor_eh_gestor(self):
        """Gestor de unidade deve ser identificado."""
        user = Usuario(id=2, empresa_id=1, perfil="gestor_unidade")
        assert user.eh_gestor() is True

    def test_operador_eh_operador(self):
        """Operador deve ser identificado."""
        user = Usuario(id=3, empresa_id=1, perfil="operador")
        assert user.eh_operador() is True

    def test_consulta_eh_consulta(self):
        """Consulta deve ser identificado."""
        user = Usuario(id=4, empresa_id=1, perfil="consulta")
        assert user.eh_consulta() is True


class TestPermissionsAcesso:
    """Testes de acesso a empresas."""

    def test_admin_acessa_qualquer_empresa(self):
        """Admin deve acessar qualquer empresa."""
        user = Usuario(id=1, empresa_id=1, perfil="admin")
        assert user.tem_acesso_empresa(1) is True
        assert user.tem_acesso_empresa(2) is True
        assert user.tem_acesso_empresa(999) is True

    def test_nao_admin_acessa_apenas_sua_empresa(self):
        """Não-admin deve acessar apenas sua empresa."""
        user = Usuario(id=2, empresa_id=1, perfil="operador")
        assert user.tem_acesso_empresa(1) is True
        assert user.tem_acesso_empresa(2) is False
        assert user.tem_acesso_empresa(999) is False

    def test_gestor_acessa_apenas_sua_empresa(self):
        """Gestor deve acessar apenas sua empresa."""
        user = Usuario(id=3, empresa_id=2, perfil="gestor_unidade")
        assert user.tem_acesso_empresa(2) is True
        assert user.tem_acesso_empresa(1) is False


class TestPermissionsCriacaoAtivos:
    """Testes de permissão para criar ativos."""

    def test_admin_pode_criar(self):
        """Admin pode criar ativos."""
        user = Usuario(id=1, empresa_id=1, perfil="admin")
        assert user.pode_criar_ativo(1) is True

    def test_gestor_pode_criar_sua_empresa(self):
        """Gestor pode criar ativos em sua empresa."""
        user = Usuario(id=2, empresa_id=1, perfil="gestor_unidade")
        assert user.pode_criar_ativo(1) is True

    def test_gestor_nao_pode_criar_outra_empresa(self):
        """Gestor não pode criar ativos em outra empresa."""
        user = Usuario(id=2, empresa_id=1, perfil="gestor_unidade")
        assert user.pode_criar_ativo(2) is False

    def test_operador_pode_criar_sua_empresa(self):
        """Operador pode criar ativos em sua empresa."""
        user = Usuario(id=3, empresa_id=1, perfil="operador")
        assert user.pode_criar_ativo(1) is True

    def test_usuario_compatibilidade_pode_criar(self):
        """Usuário Parte 1 (operador) pode criar."""
        user = Usuario(id=3, empresa_id=1, perfil="usuario")
        assert user.pode_criar_ativo(1) is True

    def test_consulta_nao_pode_criar(self):
        """Consulta não pode criar ativos."""
        user = Usuario(id=4, empresa_id=1, perfil="consulta")
        assert user.pode_criar_ativo(1) is False


class TestPermissionsRemocaoAtivos:
    """Testes de permissão para remover ativos."""

    def test_admin_pode_remover(self):
        """Admin pode remover ativos."""
        user = Usuario(id=1, empresa_id=1, perfil="admin")
        assert user.pode_remover_ativo(1) is True

    def test_gestor_pode_remover_sua_empresa(self):
        """Gestor pode remover ativos em sua empresa."""
        user = Usuario(id=2, empresa_id=1, perfil="gestor_unidade")
        assert user.pode_remover_ativo(1) is True

    def test_operador_nao_pode_remover(self):
        """Operador não pode remover (apenas admin/gestor)."""
        user = Usuario(id=3, empresa_id=1, perfil="operador")
        assert user.pode_remover_ativo(1) is False

    def test_consulta_nao_pode_remover(self):
        """Consulta não pode remover."""
        user = Usuario(id=4, empresa_id=1, perfil="consulta")
        assert user.pode_remover_ativo(1) is False


class TestPermissionsInativacaoAtivos:
    """Testes de permissão para inativar ativos."""

    def test_admin_pode_inativar(self):
        """Admin pode inativar."""
        user = Usuario(id=1, empresa_id=1, perfil="admin")
        assert user.pode_inativar_ativo(1) is True

    def test_gestor_pode_inativar(self):
        """Gestor pode inativar."""
        user = Usuario(id=2, empresa_id=1, perfil="gestor_unidade")
        assert user.pode_inativar_ativo(1) is True

    def test_operador_pode_inativar(self):
        """Operador pode inativar."""
        user = Usuario(id=3, empresa_id=1, perfil="operador")
        assert user.pode_inativar_ativo(1) is True

    def test_consulta_nao_pode_inativar(self):
        """Consulta não pode inativar."""
        user = Usuario(id=4, empresa_id=1, perfil="consulta")
        assert user.pode_inativar_ativo(1) is False


class TestPermissionsArquivos:
    """Testes de permissão para arquivos/anexos."""

    def test_admin_pode_fazer_upload(self):
        """Admin pode fazer upload."""
        user = Usuario(id=1, empresa_id=1, perfil="admin")
        assert user.pode_fazer_upload(1) is True

    def test_gestor_pode_fazer_upload(self):
        """Gestor pode fazer upload."""
        user = Usuario(id=2, empresa_id=1, perfil="gestor_unidade")
        assert user.pode_fazer_upload(1) is True

    def test_operador_pode_fazer_upload(self):
        """Operador pode fazer upload."""
        user = Usuario(id=3, empresa_id=1, perfil="operador")
        assert user.pode_fazer_upload(1) is True

    def test_consulta_nao_pode_fazer_upload(self):
        """Consulta não pode fazer upload."""
        user = Usuario(id=4, empresa_id=1, perfil="consulta")
        assert user.pode_fazer_upload(1) is False

    def test_todos_podem_visualizar_anexo(self):
        """Todos podem visualizar anexos (somente leitura)."""
        for perfil in ["admin", "gestor_unidade", "operador", "consulta"]:
            user = Usuario(id=1, empresa_id=1, perfil=perfil)
            assert user.pode_visualizar_anexo(1) is True


class TestPermissionsExportacao:
    """Testes de permissão para exportação."""

    def test_admin_pode_exportar(self):
        """Admin pode exportar."""
        user = Usuario(id=1, empresa_id=1, perfil="admin")
        assert user.pode_exportar(1) is True

    def test_gestor_pode_exportar(self):
        """Gestor pode exportar."""
        user = Usuario(id=2, empresa_id=1, perfil="gestor_unidade")
        assert user.pode_exportar(1) is True

    def test_operador_pode_exportar(self):
        """Operador pode exportar."""
        user = Usuario(id=3, empresa_id=1, perfil="operador")
        assert user.pode_exportar(1) is True

    def test_consulta_pode_exportar(self):
        """Consulta pode exportar (somente leitura, mas exportar é permitido)."""
        user = Usuario(id=4, empresa_id=1, perfil="consulta")
        assert user.pode_exportar(1) is True


class TestPermissionsAdministrativo:
    """Testes de permissões administrativas."""

    def test_apenas_admin_pode_importar(self):
        """Apenas admin pode importar."""
        admin = Usuario(id=1, empresa_id=1, perfil="admin")
        assert admin.pode_importar() is True

        for perfil in ["gestor_unidade", "operador", "consulta"]:
            user = Usuario(id=2, empresa_id=1, perfil=perfil)
            assert user.pode_importar() is False

    def test_apenas_admin_pode_acessar_auditoria(self):
        """Apenas admin pode acessar auditoria."""
        admin = Usuario(id=1, empresa_id=1, perfil="admin")
        assert admin.pode_acessar_auditoria() is True

        for perfil in ["gestor_unidade", "operador", "consulta"]:
            user = Usuario(id=2, empresa_id=1, perfil=perfil)
            assert user.pode_acessar_auditoria() is False

    def test_apenas_admin_pode_promover(self):
        """Apenas admin pode promover usuários."""
        admin = Usuario(id=1, empresa_id=1, perfil="admin")
        assert admin.pode_promover_usuario() is True

        for perfil in ["gestor_unidade", "operador", "consulta"]:
            user = Usuario(id=2, empresa_id=1, perfil=perfil)
            assert user.pode_promover_usuario() is False


class TestPermissionsDescrever:
    """Testes de descrição de perfil."""

    def test_descrever_admin(self):
        """Descrição de admin."""
        user = Usuario(id=1, empresa_id=1, perfil="admin")
        desc = user.descrever_perfil()
        assert desc["perfil"] == "admin"
        assert "total" in desc["descricao"].lower()

    def test_descrever_operador(self):
        """Descrição de operador."""
        user = Usuario(id=3, empresa_id=1, perfil="operador")
        desc = user.descrever_perfil()
        assert desc["perfil"] == "operador"
        assert "limitado" in desc["descricao"].lower()

    def test_descrever_consulta(self):
        """Descrição de consulta."""
        user = Usuario(id=4, empresa_id=1, perfil="consulta")
        desc = user.descrever_perfil()
        assert desc["perfil"] == "consulta"
        assert "leitura" in desc["descricao"].lower()


class TestPermissionsCriarContexto:
    """Testes do factory de contexto de permissão."""

    def test_criar_usuario_contexto(self):
        """Factory criar_usuario_contexto."""
        user = criar_usuario_contexto(user_id=5, empresa_id=2, perfil="operador")
        assert user.id == 5
        assert user.empresa_id == 2
        assert user.normalizar_perfil() == "operador"
        assert user.eh_operador() is True
        assert user.eh_admin() is False
