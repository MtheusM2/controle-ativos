"""
Definições de perfis, permissões e controle de acesso.

Perfis suportados:
  - 'admin': Administrador técnico (acesso total)
  - 'gestor_unidade': Gestor de unidade (acesso à sua empresa)
  - 'operador': Operador de ativos (criação/edição limitada)
  - 'consulta': Consultor (somente leitura)
  - 'usuario': Compatibilidade Parte 1 (mapeado como 'operador')

Este módulo centraliza a lógica de autorização para manter
a fonte de verdade única e facilitar auditoria.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

# Tipos de perfil válidos no sistema
PERFIS_VALIDOS = frozenset({"admin", "adm", "gestor_unidade", "operador", "consulta", "usuario"})

# Mapeamento de perfis antigos para novos (compatibilidade Parte 1)
PERFIS_COMPATIBILIDADE = {
    "usuario": "operador",  # Parte 1 usa 'usuario', mapeamos como 'operador'
    "adm": "admin",          # Aceitar 'adm' ou 'admin'
}


class Perfil(Enum):
    """Enumeração de perfis corporativos."""

    ADMIN = "admin"
    GESTOR_UNIDADE = "gestor_unidade"
    OPERADOR = "operador"
    CONSULTA = "consulta"


@dataclass(frozen=True)
class Usuario:
    """Contexto de usuário para decisões de permissão."""

    id: int
    empresa_id: int
    perfil: str

    def normalizar_perfil(self) -> str:
        """
        Normaliza o perfil para um valor canônico.
        Converte valores antigos para novos (backward compatible).
        """
        perfil_norm = (self.perfil or "").strip().lower()

        # Se estiver no mapeamento de compatibilidade, converter
        if perfil_norm in PERFIS_COMPATIBILIDADE:
            return PERFIS_COMPATIBILIDADE[perfil_norm]

        # Se for um perfil válido, retornar como está
        if perfil_norm in PERFIS_VALIDOS:
            return perfil_norm

        # Padrão seguro: se estiver corrompido, tratar como 'operador'
        return "operador"

    def eh_admin(self) -> bool:
        """Verifica se o usuário é administrador."""
        perfil = self.normalizar_perfil()
        return perfil == "admin"

    def eh_gestor(self) -> bool:
        """Verifica se é gestor de unidade."""
        perfil = self.normalizar_perfil()
        return perfil == "gestor_unidade"

    def eh_operador(self) -> bool:
        """Verifica se é operador ou acima."""
        perfil = self.normalizar_perfil()
        return perfil in {"operador", "gestor_unidade", "admin"}

    def eh_consulta(self) -> bool:
        """Verifica se é consultor (somente leitura)."""
        perfil = self.normalizar_perfil()
        return perfil == "consulta"

    def tem_acesso_empresa(self, empresa_id: int) -> bool:
        """
        Verifica se o usuário tem acesso a uma empresa.
        Admins acessam todas; outros acessam apenas sua empresa.
        """
        if self.eh_admin():
            return True
        return self.empresa_id == empresa_id

    def pode_criar_ativo(self, empresa_id: int) -> bool:
        """Verifica se pode criar um ativo."""
        if not self.tem_acesso_empresa(empresa_id):
            return False

        perfil = self.normalizar_perfil()
        return perfil in {"admin", "gestor_unidade", "operador"}

    def pode_editar_ativo(self, empresa_id: int) -> bool:
        """Verifica se pode editar um ativo."""
        if not self.tem_acesso_empresa(empresa_id):
            return False

        perfil = self.normalizar_perfil()
        return perfil in {"admin", "gestor_unidade", "operador"}

    def pode_remover_ativo(self, empresa_id: int) -> bool:
        """Verifica se pode remover um ativo (hard delete)."""
        if not self.tem_acesso_empresa(empresa_id):
            return False

        perfil = self.normalizar_perfil()
        # Apenas admin e gestor podem remover
        return perfil in {"admin", "gestor_unidade"}

    def pode_inativar_ativo(self, empresa_id: int) -> bool:
        """Verifica se pode inativar um ativo (soft delete)."""
        if not self.tem_acesso_empresa(empresa_id):
            return False

        perfil = self.normalizar_perfil()
        # Operador e acima podem inativar
        return perfil in {"admin", "gestor_unidade", "operador"}

    def pode_fazer_upload(self, empresa_id: int) -> bool:
        """Verifica se pode fazer upload de anexo."""
        if not self.tem_acesso_empresa(empresa_id):
            return False

        perfil = self.normalizar_perfil()
        return perfil in {"admin", "gestor_unidade", "operador"}

    def pode_remover_anexo(self, empresa_id: int) -> bool:
        """Verifica se pode remover anexo."""
        if not self.tem_acesso_empresa(empresa_id):
            return False

        perfil = self.normalizar_perfil()
        return perfil in {"admin", "gestor_unidade", "operador"}

    def pode_exportar(self, empresa_id: int) -> bool:
        """Verifica se pode exportar dados."""
        if not self.tem_acesso_empresa(empresa_id):
            return False

        perfil = self.normalizar_perfil()
        # Todos exceto consulta podem exportar (mas consulta pode ver dados)
        return perfil in {"admin", "gestor_unidade", "operador", "consulta"}

    def pode_importar(self) -> bool:
        """Verifica se pode importar ativos (somente admin)."""
        perfil = self.normalizar_perfil()
        return perfil == "admin"

    def pode_visualizar_ativo(self, empresa_id: int) -> bool:
        """Verifica se pode visualizar detalhe de um ativo."""
        return self.tem_acesso_empresa(empresa_id)

    def pode_visualizar_anexo(self, empresa_id: int) -> bool:
        """Verifica se pode visualizar/download de anexo."""
        return self.tem_acesso_empresa(empresa_id)

    def pode_acessar_dashboard(self) -> bool:
        """Todos podem acessar dashboard (dados filtrados por permissão)."""
        return True

    def pode_acessar_configuracoes(self) -> bool:
        """Todos podem acessar suas próprias configurações."""
        return True

    def pode_alterar_senha_propria(self) -> bool:
        """Todos podem alterar sua própria senha."""
        return True

    def pode_registrar_usuario(self) -> bool:
        """Apenas admin pode registrar novo usuário."""
        perfil = self.normalizar_perfil()
        return perfil == "admin"

    def pode_promover_usuario(self) -> bool:
        """
        Apenas admin pode promover usuários.
        Gestores podem promover apenas dentro de sua empresa (futuro).
        """
        perfil = self.normalizar_perfil()
        return perfil == "admin"

    def pode_acessar_auditoria(self) -> bool:
        """Apenas admin pode acessar logs de auditoria."""
        perfil = self.normalizar_perfil()
        return perfil == "admin"

    def descrever_perfil(self) -> dict:
        """Retorna descrição legível do perfil."""
        perfil = self.normalizar_perfil()
        descricoes = {
            "admin": "Administrador Técnico (acesso total)",
            "gestor_unidade": "Gestor de Unidade (acesso à empresa)",
            "operador": "Operador de Ativos (CRUD limitado)",
            "consulta": "Consultor (somente leitura)",
        }
        return {"perfil": perfil, "descricao": descricoes.get(perfil, "Desconhecido")}


def criar_usuario_contexto(
    user_id: int, empresa_id: int, perfil: str
) -> Usuario:
    """Factory para criar contexto de usuário."""
    return Usuario(id=user_id, empresa_id=empresa_id, perfil=perfil)
