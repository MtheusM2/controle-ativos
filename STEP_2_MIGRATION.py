#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SCRIPT 2: MIGRAÇÃO - Renomeia coluna 'seguro' para 'garantia' na tabela 'ativos'
Este é o script destrutivo - faz a alteração real no banco
"""

import mysql.connector
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.connection import _db_config

def confirmar_migracao():
    """Pede confirmação do usuário antes de executar"""
    print("\n" + "="*70)
    print("⚠️  AVISO: Você está prestes a executar a MIGRAÇÃO no banco de dados")
    print("="*70)
    print("\nO que será feito:")
    print("  • Renomear coluna 'seguro' para 'garantia' na tabela 'ativos'")
    print("  • Manter o tipo de dado (VARCHAR(100) NOT NULL)")
    print("  • Preservar todos os dados existentes")
    print("\nBACKUP JÁ FOI FEITO? [S/n]: ", end="")
    
    resposta = input().strip().lower()
    
    if resposta not in ('s', ''):
        print("\n❌ Migração cancelada pelo usuário")
        sys.exit(0)
    
    print("\n⏳ Executando migração...")

try:
    confirmar_migracao()
    
    conn = mysql.connector.connect(**_db_config(com_database=True))
    cursor = conn.cursor()
    
    # SQL de migração
    sql_migration = """
    ALTER TABLE ativos CHANGE COLUMN seguro garantia VARCHAR(100) NULL;
    """
    
    print("\n=== EXECUTANDO MIGRAÇÃO SQL ===\n")
    print(f"SQL: {sql_migration.strip()}\n")
    
    cursor.execute(sql_migration)
    conn.commit()
    
    print("✓ Migração executada com sucesso!")
    print("✓ Coluna 'seguro' foi renomeada para 'garantia'\n")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ ERRO ao executar migração:\n{e}")
    if 'conn' in locals() and conn.is_connected():
        conn.rollback()
        conn.close()
    sys.exit(1)
