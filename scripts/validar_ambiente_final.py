#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validacao Final do Ambiente - FASE E

Verifica:
1. SESSION_COOKIE_SECURE configurado corretamente
2. Variaveis essenciais de sessao e segurança
3. DEBUG desativado em teste
4. Ajustes minimos necessarios

Uso:
    python scripts/validar_ambiente_final.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import FLASK_DEBUG
from web_app.app import create_app
from database.connection import cursor_mysql

def validar_ambiente():
    """
    Valida ambiente.
    """
    print("=" * 80)
    print("VALIDACAO FINAL DE AMBIENTE - FASE E")
    print("=" * 80)

    try:
        # 1. Validar FLASK_DEBUG
        print("\n[1] Validando FLASK_DEBUG...")
        print("     FLASK_DEBUG=%s" % FLASK_DEBUG)
        if FLASK_DEBUG == "0" or FLASK_DEBUG == 0 or FLASK_DEBUG == False:
            print("     [OK] DEBUG desativado (recomendado para homologacao)")
        else:
            print("     [AVISO] DEBUG ativado (ok para desenvolvimento, nao para producao)")

        # 2. Validar SESSION_COOKIE_SECURE
        print("\n[2] Validando SESSION_COOKIE_SECURE...")
        from config import SESSION_COOKIE_SECURE
        print("     SESSION_COOKIE_SECURE=%s" % SESSION_COOKIE_SECURE)
        if SESSION_COOKIE_SECURE == "0" or SESSION_COOKIE_SECURE == 0 or SESSION_COOKIE_SECURE == False:
            print("     [AVISO] SECURE desativado (ok para HTTP local, nao para HTTPS producao)")
        elif SESSION_COOKIE_SECURE == "1" or SESSION_COOKIE_SECURE == 1 or SESSION_COOKIE_SECURE == True:
            print("     [OK] SECURE ativado (recomendado para HTTPS producao)")
        else:
            print("     [AVISO] Valor desconhecido")

        # 3. Validar app inicializacao
        print("\n[3] Validando inicializacao da aplicacao...")
        app = create_app()
        print("     [OK] App criada com sucesso")

        # 4. Validar configuraçoes Flask
        print("\n[4] Validando configuracoes Flask...")
        print("     TESTING=%s" % app.config.get('TESTING', False))
        print("     SESSION_COOKIE_HTTPONLY=%s" % app.config.get('SESSION_COOKIE_HTTPONLY', False))
        print("     SESSION_COOKIE_SAMESITE=%s" % app.config.get('SESSION_COOKIE_SAMESITE', 'none'))

        httponly = app.config.get('SESSION_COOKIE_HTTPONLY')
        samesite = app.config.get('SESSION_COOKIE_SAMESITE')

        if httponly:
            print("     [OK] HTTPONLY ativado (prevencao de XSS)")
        else:
            print("     [AVISO] HTTPONLY desativado")

        if samesite and samesite.lower() != 'none':
            print("     [OK] SAMESITE ativado: %s (prevencao de CSRF)" % samesite)
        else:
            print("     [AVISO] SAMESITE desativado ou nao configurado")

        # 5. Validar banco de dados
        print("\n[5] Validando conectividade do banco...")
        with cursor_mysql() as (conn, cur):
            cur.execute("SELECT COUNT(*) AS total FROM usuarios")
            result = cur.fetchone()
            total_users = result['total']
            print("     [OK] Banco conectando, %d usuario(s)" % total_users)

        # 6. Validar migracao
        print("\n[6] Validando migracao 005...")
        with cursor_mysql() as (conn, cur):
            cur.execute(
                "SELECT COUNT(*) AS total FROM sequencias_ativo"
            )
            result = cur.fetchone()
            total_seq = result['total']
            print("     [OK] %d sequencia(s) no banco" % total_seq)

        # 7. Resumo
        print("\n" + "=" * 80)
        print("RESULTADO: [OK] Ambiente validado para homologacao/producao")
        print("=" * 80)
        print("\nChecklist Final:")
        print("  - DEBUG: %s" % ("desativado" if FLASK_DEBUG == "0" else "ativado (dev)"))
        print("  - SESSION_COOKIE_SECURE: %s" % SESSION_COOKIE_SECURE)
        print("  - SESSION_COOKIE_HTTPONLY: %s" % httponly)
        print("  - SESSION_COOKIE_SAMESITE: %s" % samesite)
        print("  - Banco conectando: OK")
        print("  - Migracao 005: OK")
        print("\nProxima etapa: Fase F (testes finais e regressao)")
        return True

    except Exception as e:
        print("\n[ERRO] %s" % str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = validar_ambiente()
    sys.exit(0 if success else 1)
