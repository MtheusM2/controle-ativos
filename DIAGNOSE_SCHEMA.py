#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de diagnóstico: Verifica o schema atual da tabela ativos no banco MySQL.
"""

import mysql.connector
import sys
import os

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import _db_config

try:
    print("\n=== CONECTANDO AO BANCO MySQL ===")
    conn = mysql.connector.connect(**_db_config(com_database=True))
    cursor = conn.cursor(dictionary=True)
    print("✓ Conexão estabelecida com sucesso\n")
    
    # Verifica a estrutura da tabela ativos
    print("=== SCHEMA ATUAL DA TABELA 'ativos' ===\n")
    cursor.execute('DESCRIBE ativos;')
    columns = cursor.fetchall()
    
    print(f"{'Campo':<25} | {'Tipo':<20} | {'Nulo':<5} | {'Chave':<5}")
    print("-" * 70)
    for col in columns:
        col_name = col['Field']
        col_type = col['Type']
        nullable = col['Null']
        key = col['Key']
        print(f"{col_name:<25} | {col_type:<20} | {nullable:<5} | {key:<5}")
    
    print("\n=== VERIFICACAO DE COLUNAS CRITICAS ===\n")
    col_names = [col['Field'] for col in columns]
    
    seguro_exists = 'seguro' in col_names
    garantia_exists = 'garantia' in col_names
    nota_fiscal_exists = 'nota_fiscal' in col_names
    
    print(f"Coluna 'seguro' existe:      {seguro_exists}")
    print(f"Coluna 'garantia' existe:    {garantia_exists}")
    print(f"Coluna 'nota_fiscal' existe: {nota_fiscal_exists}")
    
    # Recomendação
    print("\n=== RECOMENDACAO ===\n")
    if seguro_exists and not garantia_exists:
        print("⚠️  SITUACAO: Banco ainda tem coluna 'seguro', codigo espera 'garantia'")
        print("✓  ACAO NECESSARIA: Executar migração SQL\n")
    elif not seguro_exists and garantia_exists:
        print("✓  SITUACAO: Banco ja tem coluna 'garantia', banco e codigo sincronizados")
        print("⏭️  ACAO: Nenhuma migração necessária\n")
    elif seguro_exists and garantia_exists:
        print("⚠️  SITUACAO: Ambas as colunas existem (estado intermediário)")
        print("✓  ACAO NECESSARIA: Remover coluna 'seguro' após validação\n")
    else:
        print("❌ ERRO: Nenhuma das colunas existe!")
        print("✓  ACAO: Investigar banco de dados\n")
    
    # Teste de conectividade
    print("=== TESTE DE QUERY BASICO ===\n")
    cursor.execute("SELECT COUNT(*) as total FROM ativos;")
    result = cursor.fetchone()
    print(f"Total de registros em ativos: {result['total']}")
    
    cursor.close()
    conn.close()
    print("\n✓ Diagnóstico concluído com sucesso")
    
except Exception as e:
    print(f"\n❌ ERRO ao conectar/verificar banco de dados:\n{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
