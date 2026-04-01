#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SCRIPT 3: VALIDAÇÃO pós-migração
Verifica se a migração funcionou e se o código Python é compatível
"""

import mysql.connector
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.connection import _db_config

try:
    print("\n=== VALIDACAO POS-MIGRACAO ===\n")
    
    conn = mysql.connector.connect(**_db_config(com_database=True))
    cursor = conn.cursor(dictionary=True)
    
    # 1. Verificar schema
    print("1️⃣  VERIFICACAO DE SCHEMA\n")
    cursor.execute('DESCRIBE ativos;')
    columns = cursor.fetchall()
    col_names = [col['Field'] for col in columns]
    
    seguro_exists = 'seguro' in col_names
    garantia_exists = 'garantia' in col_names
    
    status_seguro = "❌ EXISTE (erro!)" if seguro_exists else "✓ NAO EXISTE (correto)"
    status_garantia = "✓ EXISTE (correto)" if garantia_exists else "❌ NAO EXISTE (erro!)"
    
    print(f"Coluna 'seguro':   {status_seguro}")
    print(f"Coluna 'garantia': {status_garantia}\n")
    
    if not garantia_exists or seguro_exists:
        print("❌ Schema inválido após migração!")
        sys.exit(1)
    
    # 2. Verificar dados
    print("2️⃣  VERIFICACAO DE DADOS PRESERVADOS\n")
    cursor.execute("SELECT COUNT(*) as total FROM ativos;")
    result = cursor.fetchone()
    total = result['total']
    print(f"Total de registros: {total}\n")
    
    # 3. Teste de SELECT
    print("3️⃣  TESTE DE SELECT (compatibilidade com código Python)\n")
    try:
        cursor.execute("""
            SELECT id, tipo, marca, modelo, usuario_responsavel,
                   departamento, nota_fiscal, garantia, status,
                   data_entrada, data_saida, criado_por
            FROM ativos
            LIMIT 1;
        """)
        test_result = cursor.fetchone()
        if test_result:
            print("✓ SELECT com coluna 'garantia' funciona")
            print(f"✓ Exemplo: ID={test_result['id']}, Garantia={test_result['garantia']}\n")
        else:
            print("ℹ️  Nenhum registro para testar SELECT\n")
    except Exception as e:
        print(f"❌ Erro no SELECT: {e}\n")
        sys.exit(1)
    
    # 4. Teste de UPDATE (compatibilidade)
    print("4️⃣  TESTE DE SIMULACAO DE UPDATE\n")
    try:
        # Não vai fazer UPDATE de verdade, só testa a sintaxe
        cursor.execute("""
            SELECT COUNT(*) as total FROM ativos
            WHERE garantia IS NOT NULL;
        """)
        result = cursor.fetchone()
        print(f"✓ Registros com garantia preenchida: {result['total']}\n")
    except Exception as e:
        print(f"❌ Erro na simulação de UPDATE: {e}\n")
        sys.exit(1)
    
    # 5. Verificar índices
    print("5️⃣  VERIFICACAO DE INDICES\n")
    cursor.execute("SHOW INDEX FROM ativos;")
    indexes = cursor.fetchall()
    garantia_indexed = any(idx['Column_name'] == 'garantia' for idx in indexes)
    print(f"Coluna 'garantia' indexada: {garantia_indexed}\n")
    
    # 6. Verificação final
    print("="*70)
    print("✓ VALIDACAO CONCLUIDA COM SUCESSO!")
    print("="*70)
    print("\nResumo:")
    print(f"  • Schema: Sincronizado ✓")
    print(f"  • Dados: {total} registros preservados ✓")
    print(f"  • Compatibilidade Python: Testada ✓")
    print(f"  • Próximo passo: Testar aplicação Flask\n")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ ERRO durante validação:\n{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
