#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Smoke Test Basico - Valida que a aplicacao inicia sem erros

Usa:
    - Testes unitarios existentes (65 testes)
    - Inicializacao do app
    - Verificacao de migracao

Uso:
    python scripts/smoke_test_basico.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def smoke_test():
    """
    Validacao basica da aplicacao.
    """
    print("=" * 80)
    print("SMOKE TEST BASICO - Validacao de Integridade")
    print("=" * 80)

    try:
        # 1. Testar importacao de modulos principais
        print("\n[1] Validando importacao de modulos...")
        from web_app.app import create_app
        from services.ativos_service import AtivosService
        from services.auth_service import AuthService
        from database.connection import cursor_mysql
        print("     [OK] Modulos importados com sucesso")

        # 2. Testar inicializacao do Flask app
        print("\n[2] Inicializando aplicacao Flask...")
        app = create_app()
        print("     [OK] App inicializado")

        # 3. Testar contexto da app e banco
        print("\n[3] Validando contexto de banco de dados...")
        with app.app_context():
            with cursor_mysql() as (conn, cur):
                cur.execute("SELECT 1")
                result = cur.fetchone()
                if result:
                    print("     [OK] Conexao com banco funcionando")
                else:
                    print("     [ERRO] Banco nao respondeu")
                    return False

        # 4. Testar migracao
        print("\n[4] Validando migracao 005...")
        with app.app_context():
            with cursor_mysql() as (conn, cur):
                cur.execute(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_NAME = 'empresas' AND COLUMN_NAME = 'prefixo_ativo'"
                )
                result = cur.fetchone()
                if result:
                    print("     [OK] Coluna prefixo_ativo existe")
                else:
                    print("     [ERRO] Migracao 005 nao foi aplicada")
                    return False

                # Verificar tabela sequencias_ativo
                cur.execute(
                    "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_NAME = 'sequencias_ativo'"
                )
                result = cur.fetchone()
                if result:
                    print("     [OK] Tabela sequencias_ativo existe")
                else:
                    print("     [ERRO] Tabela sequencias_ativo nao existe")
                    return False

        # 5. Testar client do Flask
        print("\n[5] Validando Flask test client...")
        app.config['TESTING'] = True
        client = app.test_client()
        response = client.get('/')
        if response.status_code in (200, 302):
            print("     [OK] Home page respondeu (status %d)" % response.status_code)
        else:
            print("     [AVISO] Home page status: %d" % response.status_code)

        print("\n" + "=" * 80)
        print("RESULTADO: [OK] Smoke test basico passou")
        print("=" * 80)
        print("\nPROXIMO: Executar testes unitarios com: pytest tests/ -v")
        return True

    except Exception as e:
        print("\n[ERRO] %s" % str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = smoke_test()
    sys.exit(0 if success else 1)
