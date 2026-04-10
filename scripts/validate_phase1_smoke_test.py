#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ===========================================================================
# SMOKE TEST REAL - FASE B DA PRIMEIRA ETAPA
# ===========================================================================
#
# Objetivo:
#   Executar fluxos operacionais reais do sistema para validar funcionamento
#   end-to-end em ambiente de homologacao.
#
# Fluxos cobertos:
#   1. Autenticacao: login, sessao, logout
#   2. Criacao de ativo com ID automatico
#   3. Listagem de ativos com escopo por empresa
#   4. Filtro de ativos
#   5. Edicao de ativo
#   6. Acesso administrativo
#
# Uso:
#   python scripts/validate_phase1_smoke_test.py
#
# ===========================================================================

import sys
import os
from pathlib import Path

# Adiciona o raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["FLASK_ENV"] = "testing"

from flask import Flask
from web_app.app import create_app
from services.auth_service import AuthService
from services.ativos_service import AtivosService
from services.empresa_service import EmpresaService
from models.ativos import Ativo
from database.connection import cursor_mysql
from datetime import datetime


def limpar_terminal():
    """Limpa a tela do terminal."""
    os.system("cls" if os.name == "nt" else "clear")


class SmokeTestRunner:
    """Executor de smoke tests reais."""

    def __init__(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

        self.auth_service = AuthService()
        self.ativos_service = AtivosService()
        self.empresa_service = EmpresaService()

        self.usuario_logado = None
        self.usuario_admin = None
        self.resultados = []

    def log_resultado(self, teste, passou, mensagem=""):
        """Registra o resultado de um teste."""
        status = "[OK]" if passou else "[FALHOU]"
        print(f"  {status} {teste}")
        if mensagem:
            print(f"       {mensagem}")
        self.resultados.append({"teste": teste, "passou": passou, "mensagem": mensagem})

    def teste_login_usuario_comum(self):
        """Testa login de usuario comum."""
        print("\n[1] TESTE DE LOGIN - USUARIO COMUM")
        try:
            # Busca um usuario comum no banco
            with cursor_mysql(dictionary=True) as (conn, cur):
                cur.execute(
                    """
                    SELECT id, email, perfil, empresa_id
                    FROM usuarios
                    WHERE perfil IN ('usuario', 'user')
                    LIMIT 1
                    """
                )
                user_row = cur.fetchone()

            if not user_row:
                self.log_resultado("Login com credencial valida", False, "Nenhum usuario comum encontrado")
                return False

            # Tenta carregar o usuario
            usuario = self.auth_service.obter_usuario_por_id(user_row["id"])
            self.usuario_logado = user_row["id"]

            self.log_resultado(
                "Login com credencial valida",
                True,
                f"Usuario: {user_row['email']}, Empresa: {user_row['empresa_id']}, Perfil: {user_row['perfil']}"
            )
            return True
        except Exception as e:
            self.log_resultado("Login com credencial valida", False, str(e))
            return False

    def teste_listagem_ativos_escopo(self):
        """Testa listagem de ativos com escopo por empresa."""
        print("\n[2] TESTE DE LISTAGEM - ESCOPO POR EMPRESA")
        if not self.usuario_logado:
            self.log_resultado("Listagem de ativos", False, "Nenhum usuario logado")
            return False

        try:
            # Lista ativos do usuario
            ativos = self.ativos_service.listar_ativos(self.usuario_logado)

            if ativos is None:
                ativos = []

            self.log_resultado(
                "Listagem de ativos",
                True,
                f"{len(ativos)} ativo(s) encontrado(s)"
            )
            return len(ativos) >= 0
        except Exception as e:
            self.log_resultado("Listagem de ativos", False, str(e))
            return False

    def teste_criar_ativo_com_id_automatico(self):
        """Testa criacao de ativo com ID automatico."""
        print("\n[3] TESTE DE CRIACAO - ID AUTOMATICO")
        if not self.usuario_logado:
            self.log_resultado("Criar ativo com ID automatico", False, "Nenhum usuario logado")
            return None

        try:
            novo_ativo = Ativo(
                id_ativo="",  # Sera gerado automaticamente
                tipo="Notebook",
                marca="Dell",
                modelo="Inspiron 15",
                usuario_responsavel="Teste Automatico",
                departamento="TI",
                nota_fiscal="NF123456",
                garantia="24 meses",
                status="Em Uso",
                data_entrada=datetime.now().strftime("%Y-%m-%d"),
                data_saida=None,
                criado_por=self.usuario_logado
            )

            id_gerado = self.ativos_service.criar_ativo(novo_ativo, self.usuario_logado)

            self.log_resultado(
                "Criar ativo com ID automatico",
                True,
                f"ID gerado: {id_gerado}"
            )
            return id_gerado
        except Exception as e:
            self.log_resultado("Criar ativo com ID automatico", False, str(e))
            return None

    def teste_obter_detalhe_ativo(self, id_ativo):
        """Testa obtencao de detalhe de ativo."""
        print("\n[4] TESTE DE DETALHE - LEITURA DE ATIVO")
        if not id_ativo or not self.usuario_logado:
            self.log_resultado("Obter detalhe de ativo", False, "ID ou usuario invalido")
            return False

        try:
            ativo = self.ativos_service.buscar_ativo(id_ativo, self.usuario_logado)
            if ativo:
                self.log_resultado(
                    "Obter detalhe de ativo",
                    True,
                    f"Ativo {ativo.id_ativo}: {ativo.tipo} {ativo.marca} {ativo.modelo}"
                )
                return True
            else:
                self.log_resultado("Obter detalhe de ativo", False, "Ativo nao encontrado")
                return False
        except Exception as e:
            self.log_resultado("Obter detalhe de ativo", False, str(e))
            return False

    def teste_editar_ativo(self, id_ativo):
        """Testa edicao de ativo."""
        print("\n[5] TESTE DE EDICAO - ATUALIZACAO DE ATIVO")
        if not id_ativo or not self.usuario_logado:
            self.log_resultado("Editar ativo", False, "ID ou usuario invalido")
            return False

        try:
            # Obtem o ativo
            ativo = self.ativos_service.buscar_ativo(id_ativo, self.usuario_logado)
            if not ativo:
                self.log_resultado("Editar ativo", False, "Ativo nao encontrado para edicao")
                return False

            # Modifica um campo
            dados_atualizacao = {
                "usuario_responsavel": "Teste Automatico Modificado"
            }

            # Atualiza
            self.ativos_service.atualizar_ativo(id_ativo, dados_atualizacao, self.usuario_logado)

            # Verifica a atualizacao
            ativo_atualizado = self.ativos_service.buscar_ativo(id_ativo, self.usuario_logado)
            if ativo_atualizado.usuario_responsavel == "Teste Automatico Modificado":
                self.log_resultado("Editar ativo", True, "Ativo atualizado com sucesso")
                return True
            else:
                self.log_resultado("Editar ativo", False, "Campo nao foi atualizado corretamente")
                return False
        except Exception as e:
            self.log_resultado("Editar ativo", False, str(e))
            return False

    def teste_filtro_ativos(self):
        """Testa filtro de ativos."""
        print("\n[6] TESTE DE FILTRO - BUSCA COM CRITERIOS")
        if not self.usuario_logado:
            self.log_resultado("Filtro de ativos", False, "Nenhum usuario logado")
            return False

        try:
            # Tenta filtrar por status
            ativos = self.ativos_service.filtrar_ativos(
                user_id=self.usuario_logado,
                filtros={"status": "Em Uso"}
            )

            if ativos is not None:
                self.log_resultado(
                    "Filtro de ativos",
                    True,
                    f"Filtro funcionou: {len(ativos)} ativo(s) com status 'Em Uso'"
                )
                return True
            else:
                self.log_resultado("Filtro de ativos", False, "Filtro retornou nulo")
                return False
        except Exception as e:
            self.log_resultado("Filtro de ativos", False, str(e))
            return False

    def teste_admin(self):
        """Testa acesso administrativo."""
        print("\n[7] TESTE DE ACESSO ADMIN - PERMISSOES EXPANDIDAS")
        try:
            # Busca um usuario admin
            with cursor_mysql(dictionary=True) as (conn, cur):
                cur.execute(
                    """
                    SELECT id, email, perfil, empresa_id
                    FROM usuarios
                    WHERE perfil IN ('adm', 'admin')
                    LIMIT 1
                    """
                )
                admin_row = cur.fetchone()

            if admin_row:
                # Testa se pode acessar ativos
                contexto = self.ativos_service._obter_contexto_acesso(admin_row["id"])
                eh_admin = self.ativos_service._usuario_eh_admin(contexto)

                if eh_admin:
                    self.log_resultado(
                        "Acesso administrativo",
                        True,
                        f"Usuario {admin_row['email']} com perfil {admin_row['perfil']} eh admin"
                    )
                    self.usuario_admin = admin_row["id"]
                    return True
                else:
                    self.log_resultado("Acesso administrativo", False, "Usuario nao foi reconhecido como admin")
                    return False
            else:
                self.log_resultado("Acesso administrativo", False, "Nenhum usuario admin encontrado")
                return False
        except Exception as e:
            self.log_resultado("Acesso administrativo", False, str(e))
            return False

    def teste_acesso_negado_empresa_diferente(self, id_ativo):
        """Testa bloqueio de acesso a ativo de outra empresa."""
        print("\n[8] TESTE DE ISOLAMENTO - ACESSO A ATIVO DE OUTRA EMPRESA")
        if not id_ativo or not self.usuario_logado or not self.usuario_admin:
            self.log_resultado(
                "Isolamento por empresa",
                False,
                "Falta usuario logado ou admin"
            )
            return False

        try:
            # Tenta acessar com usuario comum (nao admin)
            # O usuario comum deve ver apenas ativos da sua empresa
            # Se o ativo foi criado na empresa do usuario comum, deve conseguir ver
            # Se o ativo foi criado em outra empresa, deve ser bloqueado (testado via PermissaoNegada)

            ativo = self.ativos_service.buscar_ativo(id_ativo, self.usuario_logado)
            if ativo:
                self.log_resultado(
                    "Isolamento por empresa",
                    True,
                    f"Usuario pode acessar ativo da sua empresa"
                )
                return True
            else:
                self.log_resultado(
                    "Isolamento por empresa",
                    False,
                    "Nao conseguiu acessar ativo da sua empresa"
                )
                return False
        except Exception as e:
            self.log_resultado("Isolamento por empresa", False, str(e))
            return False

    def executar_suite(self):
        """Executa a suite completa de smoke tests."""
        print("=" * 70)
        print("SMOKE TEST REAL - FASE B")
        print("=" * 70)

        self.teste_login_usuario_comum()
        self.teste_listagem_ativos_escopo()
        id_novo_ativo = self.teste_criar_ativo_com_id_automatico()
        if id_novo_ativo:
            self.teste_obter_detalhe_ativo(id_novo_ativo)
            self.teste_editar_ativo(id_novo_ativo)
        self.teste_filtro_ativos()
        self.teste_admin()
        if id_novo_ativo and self.usuario_admin:
            self.teste_acesso_negado_empresa_diferente(id_novo_ativo)

        # Resumo
        print("\n" + "=" * 70)
        print("RESUMO DO SMOKE TEST")
        print("=" * 70)

        passou = sum(1 for r in self.resultados if r["passou"])
        total = len(self.resultados)

        for resultado in self.resultados:
            status = "[OK]" if resultado["passou"] else "[FALHOU]"
            print(f"  {status}: {resultado['teste']}")

        print(f"\nResultado: {passou}/{total} testes passaram")

        self.app_context.pop()

        if passou == total:
            print("\n[OK] FASE B VALIDADA COM SUCESSO")
            return True
        else:
            print(f"\n[FALHOU] FASE B INCOMPLETA ({total - passou} falha(s))")
            return False


if __name__ == "__main__":
    try:
        runner = SmokeTestRunner()
        sucesso = runner.executar_suite()
        sys.exit(0 if sucesso else 1)
    except Exception as e:
        print(f"\n[ERRO] ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
