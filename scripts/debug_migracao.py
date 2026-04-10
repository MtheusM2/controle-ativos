#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import cursor_mysql

# Check if column exists first
with cursor_mysql() as (conn, cur):
    cur.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = 'empresas' AND COLUMN_NAME = 'prefixo_ativo'"
    )
    result = cur.fetchone()
    print("[DEBUG] Coluna prefixo_ativo existe?", result is not None)
    if result:
        print("[DEBUG] Coluna ja existe, nao precisa adicionar")
    else:
        print("[DEBUG] Coluna nao existe, precisa adicionar")

    # Try without IF NOT EXISTS
    print("\n[DEBUG] Tentando adicionar coluna...")
    try:
        cur.execute(
            "ALTER TABLE empresas "
            "ADD COLUMN prefixo_ativo VARCHAR(10) NULL "
            "AFTER codigo"
        )
        conn.commit()
        print("[OK] Coluna adicionada com sucesso")
    except Exception as e:
        print("[ERRO]", str(e))
        conn.rollback()
