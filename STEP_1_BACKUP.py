#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SCRIPT 1: BACKUP dos dados da tabela 'ativos' antes da migração
Salva um snapshot em CSV para segurança
"""

import mysql.connector
import csv
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.connection import _db_config

try:
    print("\n=== CRIANDO BACKUP DOS DADOS ===\n")
    
    conn = mysql.connector.connect(**_db_config(com_database=True))
    cursor = conn.cursor(dictionary=True)
    
    # Lê todos os dados da tabela
    cursor.execute("SELECT * FROM ativos;")
    rows = cursor.fetchall()
    
    # Nome do arquivo de backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"BACKUP_ativos_{timestamp}.csv"
    
    # Escreve em CSV
    if rows:
        with open(backup_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = rows[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"✓ Backup criado: {backup_file}")
        print(f"✓ Total de registros salvos: {len(rows)}\n")
    else:
        print("ℹ️  Nenhum registro para fazer backup (tabela vazia)\n")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ ERRO ao fazer backup:\n{e}")
    sys.exit(1)
