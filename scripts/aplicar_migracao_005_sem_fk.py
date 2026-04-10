#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Aplica a migracao 005 SEM FK (temporario - em producao adicione FK com usuario root).

Uso:
    python scripts/aplicar_migracao_005_sem_fk.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import conexao_mysql

def aplicar_migracao():
    """
    Aplica a migracao 005 no banco real.
    """
    print("=" * 80)
    print("APLICACAO DA MIGRACAO 005 - Geracao Automatica de ID (SEM FK)")
    print("=" * 80)
    print("[AVISO] FK sera adicionada em producao com usuario root")
    print("=" * 80)

    steps = [
        ("Selecionando banco de dados",
         "USE controle_ativos"),

        ("Adicionando coluna prefixo_ativo em empresas",
         "ALTER TABLE empresas ADD COLUMN prefixo_ativo VARCHAR(10) NULL AFTER codigo"),

        ("Criando tabela sequencias_ativo (SEM FK)",
         """CREATE TABLE IF NOT EXISTS sequencias_ativo (
            empresa_id INT NOT NULL PRIMARY KEY,
            proximo_numero INT UNSIGNED NOT NULL DEFAULT 1,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
         ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""),

        ("Configurando prefixo OPU para Opus",
         "UPDATE empresas SET prefixo_ativo = 'OPU' WHERE nome = 'Opus'"),

        ("Configurando prefixo VIC para Vicente Martins",
         "UPDATE empresas SET prefixo_ativo = 'VIC' WHERE nome = 'Vicente Martins'"),

        ("Inicializando sequencias",
         """INSERT INTO sequencias_ativo (empresa_id, proximo_numero)
            SELECT id, 1 FROM empresas WHERE prefixo_ativo IS NOT NULL
            ON DUPLICATE KEY UPDATE empresa_id = empresa_id"""),
    ]

    try:
        with conexao_mysql(com_database=False) as conn:
            cur = conn.cursor()

            for desc, sql in steps:
                print("\n[Passo] %s..." % desc)
                try:
                    cur.execute(sql)
                    rows_affected = cur.rowcount
                    print("        [OK] Linhas afetadas: %d" % rows_affected)
                except Exception as e:
                    error_msg = str(e)
                    # Se coluna ou tabela ja existe, eh ok
                    if ("Duplicate column name" in error_msg or
                        "already exists" in error_msg or
                        "Can't CREATE TABLE" in error_msg):
                        print("        [OK] Elemento ja existe, pulando")
                    else:
                        print("        [ERRO] %s" % error_msg)
                        conn.rollback()
                        return False

            conn.commit()
            cur.close()

        print("\n" + "=" * 80)
        print("RESULTADO: [OK] Migracao 005 aplicada com sucesso")
        print("[DICA] Para adicionar FK em producao, execute como root:")
        print("       ALTER TABLE sequencias_ativo")
        print("       ADD CONSTRAINT fk_seq_empresa")
        print("           FOREIGN KEY (empresa_id) REFERENCES empresas (id)")
        print("           ON DELETE RESTRICT ON UPDATE CASCADE;")
        print("=" * 80)
        return True

    except Exception as e:
        print("\n[ERRO] ao aplicar migracao: %s" % str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = aplicar_migracao()
    sys.exit(0 if success else 1)
