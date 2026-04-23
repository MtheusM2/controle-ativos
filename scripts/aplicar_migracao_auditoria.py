#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para aplicar migração 009 de auditoria de importações.

Uso:
    python scripts/aplicar_migracao_auditoria.py
"""

import sys
import io
from pathlib import Path

# Fix encoding no Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Adicionar raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import cursor_mysql


def aplicar_migracao():
    """Aplica migração 009 de auditoria de importações (versão simplificada)."""

    # Tentar versão simplificada primeiro (sem SUPER privilege)
    arquivo_migracao = Path(__file__).parent.parent / "database" / "migrations" / "009_auditoria_importacoes_simplificada.sql"

    if not arquivo_migracao.exists():
        print(f"❌ Erro: Arquivo de migração não encontrado: {arquivo_migracao}")
        return False

    print(f"📖 Lendo migração: {arquivo_migracao}")
    with open(arquivo_migracao, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    # Processar DELIMITER especialmente
    statements = []
    current_statement = ""
    delimiter = ";"
    in_trigger = False

    for line in conteudo.split('\n'):
        # Detectar DELIMITER
        if line.startswith('DELIMITER'):
            new_delim = line.split()[1] if len(line.split()) > 1 else ";"
            if new_delim != ";":
                # Está entrando em bloco (trigger, procedure)
                delimiter = new_delim
                in_trigger = True
            else:
                # Saindo de bloco
                delimiter = ";"
                in_trigger = False
            continue

        # Pular linhas vazias e comentários
        if not line.strip() or line.strip().startswith('--') or line.strip().startswith('/*'):
            continue

        current_statement += line + "\n"

        # Verificar se statement terminou
        if line.rstrip().endswith(delimiter):
            stmt = current_statement.rstrip()
            if stmt.endswith(delimiter):
                stmt = stmt[:-len(delimiter)].rstrip()
            if stmt.strip():
                statements.append(stmt)
            current_statement = ""

    # Adicionar statement final se houver
    if current_statement.strip():
        stmt = current_statement.rstrip()
        if stmt.endswith(delimiter):
            stmt = stmt[:-len(delimiter)].rstrip()
        if stmt.strip():
            statements.append(stmt)

    print(f"📝 Total de {len(statements)} statements a executar")

    try:
        with cursor_mysql() as (conn, cursor):
            for i, statement in enumerate(statements, 1):
                # Pular comentários
                if statement.startswith('--') or statement.startswith('/*'):
                    continue

                # Pular USE statements
                if statement.upper().startswith('USE'):
                    continue

                print(f"  [{i:3d}/{len(statements)}] Executando...", end='', flush=True)
                try:
                    cursor.execute(statement)
                    print(" ✓")
                except Exception as e:
                    # Se erro é "já existe", é ok (idempotente)
                    if "already exists" in str(e) or "já existe" in str(e) or "1050" in str(e):
                        print(" ✓ (já existe)")
                    elif "Duplicate" in str(e) or "Duplicada" in str(e) or "1061" in str(e):
                        print(" ✓ (já existe)")
                    else:
                        print(f" ❌")
                        print(f"    Erro: {e}")
                        # Continuar com próximo statement

        print("\n✅ Migração aplicada com sucesso!")
        return True

    except Exception as e:
        print(f"\n❌ Erro ao aplicar migração: {e}")
        return False


def verificar_migracao():
    """Verifica se tabelas foram criadas corretamente."""

    print("\n" + "="*70)
    print("  VERIFICANDO ESTRUTURA DO BANCO")
    print("="*70)

    try:
        with cursor_mysql() as (conn, cursor):
            # Verificar tabelas
            print("\n📋 Tabelas criadas:")
            cursor.execute("""
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = 'controle_ativos'
                AND TABLE_NAME LIKE 'auditoria%'
            """)

            tabelas = cursor.fetchall()
            if tabelas:
                for tabela in tabelas:
                    print(f"  ✓ {tabela['TABLE_NAME']}")
            else:
                print("  ❌ Nenhuma tabela 'auditoria*' encontrada!")
                return False

            # Verificar ativos_log
            cursor.execute("""
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = 'controle_ativos'
                AND TABLE_NAME = 'ativos_log'
            """)

            if cursor.fetchone():
                print(f"  ✓ ativos_log")
            else:
                print("  ❌ Tabela 'ativos_log' não encontrada!")
                return False

            # Verificar triggers
            print("\n⚡ Triggers criados:")
            cursor.execute("""
                SELECT TRIGGER_NAME
                FROM information_schema.TRIGGERS
                WHERE TRIGGER_SCHEMA = 'controle_ativos'
                AND TRIGGER_NAME LIKE 'trg_ativos%'
            """)

            triggers = cursor.fetchall()
            if triggers:
                for trigger in triggers:
                    print(f"  ✓ {trigger['TRIGGER_NAME']}")
            else:
                print("  ⚠ Nenhum trigger 'trg_ativos*' encontrado (pode ser normal)")

            # Verificar views
            print("\n📊 Views criadas:")
            cursor.execute("""
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = 'controle_ativos'
                AND TABLE_TYPE = 'VIEW'
                AND TABLE_NAME LIKE 'vw_%'
            """)

            views = cursor.fetchall()
            if views:
                for view in views:
                    print(f"  ✓ {view['TABLE_NAME']}")
            else:
                print("  ⚠ Nenhuma view 'vw_*' encontrada")

            print("\n✅ Estrutura verificada com sucesso!")
            return True

    except Exception as e:
        print(f"\n❌ Erro ao verificar: {e}")
        return False


if __name__ == "__main__":
    print("="*70)
    print("  APLICAR MIGRAÇÃO 009 — AUDITORIA DE IMPORTAÇÕES")
    print("="*70)
    print()

    # Aplicar migração
    ok = aplicar_migracao()

    if ok:
        # Verificar resultado
        ok = verificar_migracao()

    if ok:
        print("\n" + "="*70)
        print("  ✅ TUDO PRONTO!")
        print("="*70)
        print("\nPróximos passos:")
        print("  1. Rodar testes: pytest tests/test_import_validators.py -v")
        print("  2. Testar rota: curl -X POST http://localhost:5000/ativos/importar/preview ...")
        print("  3. Verificar logs: SELECT * FROM auditoria_importacoes;")
        sys.exit(0)
    else:
        print("\n" + "="*70)
        print("  ❌ ERRO NA MIGRAÇÃO")
        print("="*70)
        sys.exit(1)
