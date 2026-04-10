#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Corrige permissoes do usuario opus_app para permitir REFERENCES em migracao 005.

Usa conexao com usuarios administrativos (root ou com privilegi suficiente).

Uso:
    python scripts/corrigir_permissoes_opus_app.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import mysql.connector
from config import DB_HOST, DB_PORT, DB_NAME

def corrigir_permissoes():
    """
    Corrige permissoes de opus_app.
    """
    print("=" * 80)
    print("CORRECAO DE PERMISSOES - opus_app")
    print("=" * 80)

    # Tenta conectar como root (sem senha - pode falhar, eh esperado)
    print("\n[Tentativa] Conectando como root para corrigir permissoes...")

    # Primeiro, tenta sem senha (localhost, root)
    configs_tentativa = [
        {
            "host": DB_HOST,
            "port": DB_PORT,
            "user": "root",
            "password": "",  # sem senha
            "desc": "root sem senha"
        },
        {
            "host": DB_HOST,
            "port": DB_PORT,
            "user": "root",
            "password": "root",  # senha comum
            "desc": "root/root"
        },
    ]

    for config_attempt in configs_tentativa:
        try:
            print("  Tentando %s..." % config_attempt["desc"])
            conn = mysql.connector.connect(
                host=config_attempt["host"],
                port=config_attempt["port"],
                user=config_attempt["user"],
                password=config_attempt["password"]
            )

            cur = conn.cursor()

            # Adiciona permissao REFERENCES
            print("\n[Passo] Adicionando permissao REFERENCES para opus_app...")
            sql = "GRANT REFERENCES ON `%s`.* TO 'opus_app'@'localhost'" % DB_NAME
            try:
                cur.execute(sql)
                print("        [OK] Permissao REFERENCES adicionada")
            except Exception as e:
                print("        [AVISO] %s" % str(e))

            # Flush privileges
            print("\n[Passo] Recarregando tabela de privilegios...")
            try:
                cur.execute("FLUSH PRIVILEGES")
                print("        [OK] Privilegios recarregados")
            except Exception as e:
                print("        [AVISO] %s" % str(e))

            conn.commit()
            cur.close()
            conn.close()

            print("\n" + "=" * 80)
            print("RESULTADO: [OK] Permissoes corrigidas com sucesso")
            print("=" * 80)
            return True

        except Exception as e:
            print("  Falhou: %s" % str(e))
            continue

    print("\n[ERRO] Nenhuma credencial de admin funcionou")
    print("[DICA] Execute manualmente:")
    print("       mysql -u root -p")
    print("       GRANT REFERENCES ON controle_ativos.* TO 'opus_app'@'localhost';")
    print("       FLUSH PRIVILEGES;")
    return False

if __name__ == '__main__':
    success = corrigir_permissoes()
    sys.exit(0 if success else 1)
