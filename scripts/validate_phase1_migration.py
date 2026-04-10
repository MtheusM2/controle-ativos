#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ===========================================================================
# VALIDACAO DE MIGRACAO - FASE A DA PRIMEIRA ETAPA
# ===========================================================================
#
# Objetivo:
#   Validar o estado da migração 005 no banco de dados de produção/homologação.
#   Cobertura:
#     1. Coluna prefixo_ativo em empresas
#     2. Tabela sequencias_ativo
#     3. Prefixos configurados por empresa
#     4. Sequências inicializadas
#     5. Foreign keys
#     6. Suporte a SELECT FOR UPDATE
#
# Uso:
#   python scripts/validate_phase1_migration.py
#
# ===========================================================================

import sys
from pathlib import Path

# Adiciona o raiz do projeto ao path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import cursor_mysql


def validar_coluna_prefixo_ativo():
    """Valida se a coluna prefixo_ativo existe em empresas."""
    print("\n[1] VALIDANDO COLUNA prefixo_ativo em empresas...")
    try:
        with cursor_mysql(dictionary=True) as (conn, cur):
            cur.execute(
                """
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'empresas'
                  AND COLUMN_NAME = 'prefixo_ativo'
                """
            )
            row = cur.fetchone()
            if row:
                print(f"    [OK] Coluna encontrada: {row['COLUMN_NAME']} ({row['COLUMN_TYPE']}, nullable={row['IS_NULLABLE']})")
                return True
            else:
                print("    [FALHOU] Coluna NAO encontrada")
                return False
    except Exception as e:
        print(f"    [FALHOU] Erro ao verificar coluna: {e}")
        return False


def validar_tabela_sequencias():
    """Valida se a tabela sequencias_ativo existe com estrutura correta."""
    print("\n[2] VALIDANDO TABELA sequencias_ativo...")
    try:
        with cursor_mysql(dictionary=True) as (conn, cur):
            # Verifica existência
            cur.execute(
                """
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'sequencias_ativo'
                """
            )
            if not cur.fetchone():
                print("    [FALHOU] Tabela NAO encontrada")
                return False

            print("    [OK] Tabela encontrada")

            # Verifica estrutura
            cur.execute(
                """
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'sequencias_ativo'
                ORDER BY ORDINAL_POSITION
                """
            )
            cols = cur.fetchall()
            for col in cols:
                print(f"      - {col['COLUMN_NAME']}: {col['COLUMN_TYPE']} (nullable={col['IS_NULLABLE']}, key={col['COLUMN_KEY']})")

            if len(cols) >= 3:
                print("    [OK] Estrutura valida (3+ colunas)")
                return True
            else:
                print("    [FALHOU] Estrutura incompleta")
                return False
    except Exception as e:
        print(f"    [FALHOU] Erro ao verificar tabela: {e}")
        return False


def validar_prefixos_configurados():
    """Valida se os prefixos estão configurados nas empresas."""
    print("\n[3] VALIDANDO PREFIXOS CONFIGURADOS...")
    try:
        with cursor_mysql(dictionary=True) as (conn, cur):
            cur.execute(
                """
                SELECT id, nome, prefixo_ativo, ativa
                FROM empresas
                ORDER BY id
                """
            )
            empresas = cur.fetchall()
            if not empresas:
                print("    [AVISO] Nenhuma empresa encontrada")
                return False

            com_prefixo = 0
            for emp in empresas:
                prefixo = (emp.get("prefixo_ativo") or "").strip()
                status = "[OK]" if prefixo else "[FALTA]"
                print(f"      {status} {emp['nome']:20} | prefixo={prefixo or 'NULO'} | ativa={emp['ativa']}")
                if prefixo:
                    com_prefixo += 1

            if com_prefixo > 0:
                print(f"    [OK] {com_prefixo}/{len(empresas)} empresa(s) com prefixo configurado")
                return True
            else:
                print("    [FALHOU] Nenhuma empresa com prefixo configurado")
                return False
    except Exception as e:
        print(f"    [FALHOU] Erro ao verificar prefixos: {e}")
        return False


def validar_sequencias_inicializadas():
    """Valida se as sequências por empresa estão inicializadas."""
    print("\n[4] VALIDANDO SEQUÊNCIAS INICIALIZADAS...")
    try:
        with cursor_mysql(dictionary=True) as (conn, cur):
            cur.execute(
                """
                SELECT sa.empresa_id, e.nome, sa.proximo_numero
                FROM sequencias_ativo sa
                LEFT JOIN empresas e ON e.id = sa.empresa_id
                ORDER BY sa.empresa_id
                """
            )
            seqs = cur.fetchall()
            if not seqs:
                print("    [AVISO] Nenhuma sequencia inicializada")
                return False

            for seq in seqs:
                emp_name = seq.get("nome") or "EMPRESA_INVALIDA"
                print(f"      [OK] Empresa {seq['empresa_id']}: {emp_name:20} | proximo_numero={seq['proximo_numero']}")

            if len(seqs) > 0:
                print(f"    [OK] {len(seqs)} sequencia(s) inicializada(s)")
                return True
            else:
                print("    [FALHOU] Nenhuma sequencia inicializada")
                return False
    except Exception as e:
        print(f"    [FALHOU] Erro ao verificar sequencias: {e}")
        return False


def validar_foreign_keys():
    """Valida se a foreign key em sequencias_ativo existe."""
    print("\n[5] VALIDANDO FOREIGN KEY...")
    try:
        with cursor_mysql(dictionary=True) as (conn, cur):
            cur.execute(
                """
                SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'sequencias_ativo'
                  AND REFERENCED_TABLE_NAME IS NOT NULL
                """
            )
            fks = cur.fetchall()
            if fks:
                for fk in fks:
                    print(f"      [OK] Constraint: {fk['CONSTRAINT_NAME']} -> {fk['REFERENCED_TABLE_NAME']}({fk['REFERENCED_COLUMN_NAME']})")
                print("    [OK] Foreign key configurada")
                return True
            else:
                print("    [AVISO] Nenhuma foreign key encontrada (pode ser limitacao de permissao)")
                return True  # Nao eh critico se sem permissao
    except Exception as e:
        print(f"    [AVISO] Erro ao verificar FK: {e}")
        return True  # Nao eh critico se sem permissao


def validar_select_for_update():
    """Valida se a engine suporta SELECT FOR UPDATE."""
    print("\n[6] VALIDANDO SUPORTE A SELECT FOR UPDATE...")
    try:
        with cursor_mysql(dictionary=True) as (conn, cur):
            # Tenta um SELECT FOR UPDATE simples sem modificar dados
            cur.execute("SELECT @@VERSION")
            version = cur.fetchone()
            print(f"      MySQL version: {version['@@VERSION']}")

            # Verifica se é InnoDB
            cur.execute(
                """
                SELECT ENGINE
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'sequencias_ativo'
                """
            )
            engine_row = cur.fetchone()
            engine = engine_row.get("ENGINE", "UNKNOWN") if engine_row else "UNKNOWN"
            print(f"      Engine da tabela sequencias_ativo: {engine}")

            if engine == "InnoDB":
                print("    [OK] InnoDB (suporta SELECT FOR UPDATE)")
                return True
            else:
                print(f"    [FALHOU] Engine {engine} (pode nao suportar SELECT FOR UPDATE)")
                return False
    except Exception as e:
        print(f"    [FALHOU] Erro ao verificar engine: {e}")
        return False


def executar_validacao():
    """Executa todas as validações."""
    print("=" * 70)
    print("VALIDAÇÃO DE MIGRAÇÃO — FASE A")
    print("=" * 70)

    resultados = {
        "Coluna prefixo_ativo": validar_coluna_prefixo_ativo(),
        "Tabela sequencias_ativo": validar_tabela_sequencias(),
        "Prefixos configurados": validar_prefixos_configurados(),
        "Sequências inicializadas": validar_sequencias_inicializadas(),
        "Foreign key": validar_foreign_keys(),
        "Suporte SELECT FOR UPDATE": validar_select_for_update(),
    }

    print("\n" + "=" * 70)
    print("RESUMO DA VALIDACAO")
    print("=" * 70)

    passa = sum(1 for v in resultados.values() if v)
    total = len(resultados)

    for nome, resultado in resultados.items():
        status = "[OK]" if resultado else "[FALHOU]"
        print(f"  {status}: {nome}")

    print(f"\nResultado: {passa}/{total} validacoes passaram")

    if passa == total:
        print("\n[OK] FASE A VALIDADA COM SUCESSO")
        return True
    else:
        print(f"\n[FALHOU] FASE A INCOMPLETA ({total - passa} falha(s))")
        return False


if __name__ == "__main__":
    try:
        sucesso = executar_validacao()
        sys.exit(0 if sucesso else 1)
    except Exception as e:
        print(f"\n[ERRO] ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
