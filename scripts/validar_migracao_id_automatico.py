#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validacao da Migracao 005: Geracao Automatica de ID de Ativo
Verifica status real da migration no banco.

Uso:
    python scripts/validar_migracao_id_automatico.py
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import cursor_mysql

def validar_migracao():
    """
    Valida a migracao 005 no banco real.
    """
    print("=" * 80)
    print("VALIDACAO DA MIGRACAO 005 - Geracao Automatica de ID")
    print("=" * 80)

    try:
        with cursor_mysql() as (conn, cur):
            # 1. Verificar se coluna prefixo_ativo existe em empresas
            print("\n[1] Verificando coluna prefixo_ativo em empresas...")
            cur.execute(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_NAME = 'empresas' AND COLUMN_NAME = 'prefixo_ativo' "
                "AND TABLE_SCHEMA = DATABASE()"
            )
            result = cur.fetchone()
            if result:
                print("     [OK] Coluna prefixo_ativo existe em empresas")
            else:
                print("     [ERRO] Coluna prefixo_ativo NAO existe em empresas")
                return False

            # 2. Verificar se tabela sequencias_ativo existe
            print("\n[2] Verificando tabela sequencias_ativo...")
            cur.execute(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                "WHERE TABLE_NAME = 'sequencias_ativo' AND TABLE_SCHEMA = DATABASE()"
            )
            result = cur.fetchone()
            if result:
                print("     [OK] Tabela sequencias_ativo existe")
            else:
                print("     [ERRO] Tabela sequencias_ativo NAO existe")
                return False

            # 3. Verificar estrutura de sequencias_ativo
            print("\n[3] Verificando estrutura de sequencias_ativo...")
            cur.execute("DESCRIBE sequencias_ativo")
            columns = cur.fetchall()
            expected_cols = {'empresa_id', 'proximo_numero', 'updated_at'}
            actual_cols = {col['Field'] for col in columns}

            if expected_cols.issubset(actual_cols):
                print("     [OK] Estrutura de sequencias_ativo correta")
                for col in columns:
                    print("        - %s: %s" % (col['Field'], col['Type']))
            else:
                print("     [ERRO] Faltam colunas: %s" % (expected_cols - actual_cols))
                return False

            # 4. Verificar engine de sequencias_ativo
            print("\n[4] Verificando engine de sequencias_ativo...")
            cur.execute(
                "SELECT ENGINE FROM INFORMATION_SCHEMA.TABLES "
                "WHERE TABLE_NAME = 'sequencias_ativo' AND TABLE_SCHEMA = DATABASE()"
            )
            result = cur.fetchone()
            if result and result['ENGINE'] == 'InnoDB':
                print("     [OK] Engine: %s (suporta SELECT FOR UPDATE)" % result['ENGINE'])
            else:
                print("     [AVISO] Engine: %s" % (result['ENGINE'] if result else 'desconhecido'))

            # 5. Verificar FK em sequencias_ativo
            print("\n[5] Verificando Foreign Key...")
            cur.execute(
                "SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
                "WHERE TABLE_NAME = 'sequencias_ativo' AND COLUMN_NAME = 'empresa_id' "
                "AND REFERENCED_TABLE_NAME = 'empresas' AND TABLE_SCHEMA = DATABASE()"
            )
            result = cur.fetchone()
            if result:
                print("     [OK] FK existe: %s" % result['CONSTRAINT_NAME'])
            else:
                print("     [AVISO] FK nao encontrada (sera adicionada com permissao root em producao)")

            # 6. Verificar prefixo OPU (Opus)
            print("\n[6] Verificando prefixo OPU (Opus)...")
            cur.execute("SELECT id, nome, prefixo_ativo FROM empresas WHERE nome = 'Opus'")
            result = cur.fetchone()
            if result:
                if result['prefixo_ativo'] == 'OPU':
                    print("     [OK] Opus (id=%s) com prefixo OPU" % result['id'])
                else:
                    print("     [ERRO] Opus com prefixo '%s' (esperado: OPU)" % result['prefixo_ativo'])
                    return False
            else:
                print("     [AVISO] Empresa 'Opus' nao encontrada")

            # 7. Verificar prefixo VIC (Vicente Martins)
            print("\n[7] Verificando prefixo VIC (Vicente Martins)...")
            cur.execute("SELECT id, nome, prefixo_ativo FROM empresas WHERE nome = 'Vicente Martins'")
            result = cur.fetchone()
            if result:
                if result['prefixo_ativo'] == 'VIC':
                    print("     [OK] Vicente Martins (id=%s) com prefixo VIC" % result['id'])
                else:
                    print("     [ERRO] Vicente Martins com prefixo '%s' (esperado: VIC)" % result['prefixo_ativo'])
                    return False
            else:
                print("     [AVISO] Empresa 'Vicente Martins' nao encontrada")

            # 8. Verificar sequencias inicializadas
            print("\n[8] Verificando inicializacao de sequencias...")
            cur.execute(
                "SELECT sa.empresa_id, e.nome, sa.proximo_numero FROM sequencias_ativo sa "
                "LEFT JOIN empresas e ON sa.empresa_id = e.id "
                "ORDER BY sa.empresa_id"
            )
            results = cur.fetchall()
            if results:
                print("     [OK] %d sequencia(s) inicializada(s):" % len(results))
                for row in results:
                    print("        - Empresa %d (%s): proximo=%d" % (row['empresa_id'], row['nome'], row['proximo_numero']))
            else:
                print("     [ERRO] Nenhuma sequencia inicializada")
                return False

            # 9. Verificar consistencia: empresas com prefixo devem ter sequencia
            print("\n[9] Verificando consistencia prefixo <-> sequencia...")
            cur.execute(
                "SELECT e.id, e.nome, e.prefixo_ativo, COUNT(sa.empresa_id) AS tem_seq "
                "FROM empresas e LEFT JOIN sequencias_ativo sa ON e.id = sa.empresa_id "
                "WHERE e.prefixo_ativo IS NOT NULL "
                "GROUP BY e.id, e.nome, e.prefixo_ativo"
            )
            results = cur.fetchall()
            all_consistent = True
            for row in results:
                if row['tem_seq'] > 0:
                    print("     [OK] %s (prefixo=%s): sequencia OK" % (row['nome'], row['prefixo_ativo']))
                else:
                    print("     [ERRO] %s (prefixo=%s): SEM sequencia!" % (row['nome'], row['prefixo_ativo']))
                    all_consistent = False

            if not all_consistent:
                return False

        print("\n" + "=" * 80)
        print("RESULTADO: [OK] Migracao 005 validada com sucesso")
        print("=" * 80)
        return True

    except Exception as e:
        print("\n[ERRO] ao validar migracao: %s" % str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = validar_migracao()
    sys.exit(0 if success else 1)
