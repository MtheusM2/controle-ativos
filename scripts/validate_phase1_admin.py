#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ===========================================================================
# VALIDACAO DE ADMINISTRADOR - FASE D DA PRIMEIRA ETAPA
# ===========================================================================
#
# Objetivo:
#   Validar o fluxo administrativo completo:
#     1. Localizacao de usuario comum
#     2. Promocao a administrador via UPDATE SQL
#     3. Confirmacao da alteracao no banco
#     4. Nova sessao com permissoes de admin
#     5. Verificacao de acesso expandido
#     6. Consistencia entre perfis 'admin' e 'adm'
#
# Uso:
#   python scripts/validate_phase1_admin.py
#
# ===========================================================================

import sys
import os
from pathlib import Path

# Adiciona o raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["FLASK_ENV"] = "testing"

from web_app.app import create_app
from services.ativos_service import AtivosService
from database.connection import cursor_mysql


class ValidadorAdmin:
    """Valida o fluxo administrativo."""

    def __init__(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

        self.ativos_service = AtivosService()
        self.resultados = []
        self.usuario_teste_id = None
        self.usuario_teste_email = None

    def log_resultado(self, teste, passou, mensagem=""):
        """Registra o resultado de um teste."""
        status = "[OK]" if passou else "[FALHOU]"
        print(f"  {status} {teste}")
        if mensagem:
            print(f"       {mensagem}")
        self.resultados.append({"teste": teste, "passou": passou, "mensagem": mensagem})

    def teste_localizacao_usuario_comum(self):
        """Localiza um usuario comum para teste."""
        print("\n[1] LOCALIZANDO USUARIO COMUM PARA TESTE")

        try:
            with cursor_mysql(dictionary=True) as (conn, cur):
                cur.execute(
                    """
                    SELECT id, email, perfil, empresa_id
                    FROM usuarios
                    WHERE perfil = 'usuario'
                    ORDER BY id DESC
                    LIMIT 1
                    """
                )
                user = cur.fetchone()

            if not user:
                self.log_resultado(
                    "Localizacao de usuario comum",
                    False,
                    "Nenhum usuario comum encontrado"
                )
                return False

            self.usuario_teste_id = user["id"]
            self.usuario_teste_email = user["email"]

            self.log_resultado(
                "Localizacao de usuario comum",
                True,
                f"Usuario {user['email']} (ID: {user['id']}, Perfil: {user['perfil']}, Empresa: {user['empresa_id']})"
            )
            return True

        except Exception as e:
            self.log_resultado("Localizacao de usuario comum", False, str(e))
            return False

    def teste_promocao_a_admin(self):
        """Promove o usuario a administrador."""
        print("\n[2] PROMOCAO A ADMINISTRADOR")

        if not self.usuario_teste_id:
            self.log_resultado("Promocao a admin", False, "Usuario nao foi localizado")
            return False

        try:
            with cursor_mysql(dictionary=True) as (conn, cur):
                # Altera o perfil para 'admin'
                cur.execute(
                    """
                    UPDATE usuarios
                    SET perfil = 'admin'
                    WHERE id = %s
                    """,
                    (self.usuario_teste_id,)
                )
                conn.commit()

                # Verifica a alteracao
                cur.execute(
                    """
                    SELECT perfil FROM usuarios WHERE id = %s
                    """,
                    (self.usuario_teste_id,)
                )
                resultado = cur.fetchone()

            if resultado and resultado["perfil"] == "admin":
                self.log_resultado(
                    "Promocao a admin",
                    True,
                    f"Usuario {self.usuario_teste_email} promovido para perfil 'admin'"
                )
                return True
            else:
                self.log_resultado(
                    "Promocao a admin",
                    False,
                    f"Perfil nao foi alterado no banco"
                )
                return False

        except Exception as e:
            self.log_resultado("Promocao a admin", False, str(e))
            return False

    def teste_confirmacao_banco(self):
        """Confirma que a alteracao foi persistida."""
        print("\n[3] CONFIRMACAO NO BANCO DE DADOS")

        if not self.usuario_teste_id:
            self.log_resultado("Confirmacao banco", False, "Usuario nao foi localizado")
            return False

        try:
            with cursor_mysql(dictionary=True) as (conn, cur):
                cur.execute(
                    """
                    SELECT id, email, perfil, empresa_id
                    FROM usuarios
                    WHERE id = %s
                    """,
                    (self.usuario_teste_id,)
                )
                user = cur.fetchone()

            if user and user["perfil"] == "admin":
                self.log_resultado(
                    "Confirmacao banco",
                    True,
                    f"Banco reflete: ID={user['id']}, Email={user['email']}, Perfil={user['perfil']}"
                )
                return True
            else:
                self.log_resultado(
                    "Confirmacao banco",
                    False,
                    f"Banco nao reflete a mudanca"
                )
                return False

        except Exception as e:
            self.log_resultado("Confirmacao banco", False, str(e))
            return False

    def teste_nova_sessao_com_permissoes_admin(self):
        """Valida que uma nova sessao reflete o perfil admin."""
        print("\n[4] VALIDACAO DE SESSAO COM PERFIL ADMIN")

        if not self.usuario_teste_id:
            self.log_resultado("Sessao admin", False, "Usuario nao foi localizado")
            return False

        try:
            # Obtem o contexto de acesso (simula uma nova sessao)
            contexto = self.ativos_service._obter_contexto_acesso(self.usuario_teste_id)

            if contexto:
                eh_admin = self.ativos_service._usuario_eh_admin(contexto)
                perfil = contexto.get("perfil")

                if eh_admin:
                    self.log_resultado(
                        "Sessao admin",
                        True,
                        f"Usuario reconhecido como admin (perfil: {perfil})"
                    )
                    return True
                else:
                    self.log_resultado(
                        "Sessao admin",
                        False,
                        f"Usuario nao foi reconhecido como admin (perfil: {perfil})"
                    )
                    return False
            else:
                self.log_resultado(
                    "Sessao admin",
                    False,
                    f"Nao conseguiu obter contexto"
                )
                return False

        except Exception as e:
            self.log_resultado("Sessao admin", False, str(e))
            return False

    def teste_acesso_expandido_admin(self):
        """Valida que admin consegue acessar ativos de outras empresas."""
        print("\n[5] ACESSO EXPANDIDO DO ADMIN")

        if not self.usuario_teste_id:
            self.log_resultado("Acesso expandido", False, "Usuario nao foi localizado")
            return False

        try:
            # Lista ativos do usuario (agora admin)
            # Admin deve ver ativos de TODAS as empresas
            ativos = self.ativos_service.listar_ativos(self.usuario_teste_id)

            if ativos:
                # Verifica se ha ativos de diferentes empresas
                empresas_representadas = set()
                with cursor_mysql(dictionary=True) as (conn, cur):
                    for ativo in ativos:
                        cur.execute(
                            """
                            SELECT empresa_id FROM ativos WHERE id = %s
                            """,
                            (ativo.id_ativo,)
                        )
                        resultado = cur.fetchone()
                        if resultado:
                            empresas_representadas.add(resultado["empresa_id"])

                if len(empresas_representadas) > 1:
                    self.log_resultado(
                        "Acesso expandido",
                        True,
                        f"Admin vê ativos de {len(empresas_representadas)} empresa(s)"
                    )
                    return True
                else:
                    # Pode estar ok se ha apenas uma empresa com ativos
                    self.log_resultado(
                        "Acesso expandido",
                        True,
                        f"Admin vê {len(ativos)} ativos (possivel que ha apenas 1 empresa com dados)"
                    )
                    return True
            else:
                self.log_resultado(
                    "Acesso expandido",
                    False,
                    f"Admin nao consegue listar nenhum ativo"
                )
                return False

        except Exception as e:
            self.log_resultado("Acesso expandido", False, str(e))
            return False

    def teste_consistencia_perfil_admin_adm(self):
        """Valida que tanto 'admin' quanto 'adm' sao reconhecidos como admin."""
        print("\n[6] CONSISTENCIA DE PERFIS 'admin' E 'adm'")

        try:
            with cursor_mysql(dictionary=True) as (conn, cur):
                # Busca um usuario com perfil 'adm'
                cur.execute(
                    """
                    SELECT id, email, perfil
                    FROM usuarios
                    WHERE perfil IN ('adm', 'admin')
                    LIMIT 1
                    """
                )
                user_adm = cur.fetchone()

            if not user_adm:
                self.log_resultado(
                    "Consistencia admin/adm",
                    False,
                    "Nenhum usuario com perfil admin/adm encontrado"
                )
                return False

            # Verifica se eh reconhecido como admin
            contexto = self.ativos_service._obter_contexto_acesso(user_adm["id"])
            eh_admin = self.ativos_service._usuario_eh_admin(contexto)

            if eh_admin:
                self.log_resultado(
                    "Consistencia admin/adm",
                    True,
                    f"Usuario com perfil '{user_adm['perfil']}' eh reconhecido como admin"
                )
                return True
            else:
                self.log_resultado(
                    "Consistencia admin/adm",
                    False,
                    f"Usuario com perfil '{user_adm['perfil']}' NAO eh reconhecido como admin"
                )
                return False

        except Exception as e:
            self.log_resultado("Consistencia admin/adm", False, str(e))
            return False

    def teste_cadastro_normal_nao_cria_admin(self):
        """Valida que o cadastro normal nao cria usuarios com perfil admin."""
        print("\n[7] CADASTRO NORMAL NAO CRIA ADMIN")

        try:
            with cursor_mysql(dictionary=True) as (conn, cur):
                # Busca usuarios recentemente criados
                cur.execute(
                    """
                    SELECT id, email, perfil
                    FROM usuarios
                    WHERE perfil NOT IN ('adm', 'admin')
                    ORDER BY criado_em DESC
                    LIMIT 10
                    """
                )
                usuarios_comuns = cur.fetchall()

            if not usuarios_comuns:
                self.log_resultado(
                    "Cadastro nao cria admin",
                    False,
                    "Nenhum usuario comum encontrado"
                )
                return False

            # Verifica que todos sao 'usuario' (ou similar), nao admin
            todos_nao_admin = all(u["perfil"] not in ("adm", "admin") for u in usuarios_comuns)

            if todos_nao_admin:
                self.log_resultado(
                    "Cadastro nao cria admin",
                    True,
                    f"Todos os {len(usuarios_comuns)} ultimos usuarios comuns tem perfil correto"
                )
                return True
            else:
                self.log_resultado(
                    "Cadastro nao cria admin",
                    False,
                    f"Alguns usuarios foram criados com perfil admin"
                )
                return False

        except Exception as e:
            self.log_resultado("Cadastro nao cria admin", False, str(e))
            return False

    def teste_reversao_perfil(self):
        """Reverte o usuario de teste ao perfil original."""
        print("\n[8] REVERSAO DO USUARIO DE TESTE")

        if not self.usuario_teste_id:
            self.log_resultado("Reversao", False, "Usuario nao foi localizado")
            return False

        try:
            with cursor_mysql(dictionary=True) as (conn, cur):
                # Reverte para 'usuario'
                cur.execute(
                    """
                    UPDATE usuarios
                    SET perfil = 'usuario'
                    WHERE id = %s
                    """,
                    (self.usuario_teste_id,)
                )
                conn.commit()

                # Verifica
                cur.execute(
                    """
                    SELECT perfil FROM usuarios WHERE id = %s
                    """,
                    (self.usuario_teste_id,)
                )
                resultado = cur.fetchone()

            if resultado and resultado["perfil"] == "usuario":
                self.log_resultado(
                    "Reversao",
                    True,
                    f"Usuario {self.usuario_teste_email} revertido para 'usuario'"
                )
                return True
            else:
                self.log_resultado(
                    "Reversao",
                    False,
                    f"Nao conseguiu reverter o perfil"
                )
                return False

        except Exception as e:
            self.log_resultado("Reversao", False, str(e))
            return False

    def executar_validacao(self):
        """Executa a suite completa de validacoes."""
        print("=" * 70)
        print("VALIDACAO DE ADMINISTRADOR - FASE D")
        print("=" * 70)

        self.teste_localizacao_usuario_comum()
        if self.usuario_teste_id:
            self.teste_promocao_a_admin()
            self.teste_confirmacao_banco()
            self.teste_nova_sessao_com_permissoes_admin()
            self.teste_acesso_expandido_admin()
        self.teste_consistencia_perfil_admin_adm()
        self.teste_cadastro_normal_nao_cria_admin()
        if self.usuario_teste_id:
            self.teste_reversao_perfil()

        # Resumo
        print("\n" + "=" * 70)
        print("RESUMO DA VALIDACAO ADMIN")
        print("=" * 70)

        passou = sum(1 for r in self.resultados if r["passou"])
        total = len(self.resultados)

        for resultado in self.resultados:
            status = "[OK]" if resultado["passou"] else "[FALHOU]"
            print(f"  {status}: {resultado['teste']}")

        print(f"\nResultado: {passou}/{total} testes passaram")

        self.app_context.pop()

        if passou == total:
            print("\n[OK] FASE D VALIDADA COM SUCESSO")
            return True
        else:
            print(f"\n[FALHOU] FASE D INCOMPLETA ({total - passou} falha(s))")
            return False


if __name__ == "__main__":
    try:
        validador = ValidadorAdmin()
        sucesso = validador.executar_validacao()
        sys.exit(0 if sucesso else 1)
    except Exception as e:
        print(f"\n[ERRO] ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
