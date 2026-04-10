#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup de dados para teste de ID automatico

Cria:
1. Prefixo OPU para Opus Medical
2. Usuario teste em Vicente Martins
"""

import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import conexao_mysql
from utils.crypto import gerar_hash

def setup():
    """
    Setup de dados.
    """
    print("=" * 80)
    print("SETUP DE DADOS PARA TESTE DE ID AUTOMATICO")
    print("=" * 80)

    try:
        with conexao_mysql(com_database=False) as conn:
            cur = conn.cursor()

            # 1. Adicionar prefixo OPU em Opus Medical
            print("\n[1] Adicionando prefixo OPU em Opus Medical...")
            try:
                cur.execute(
                    "UPDATE controle_ativos.empresas SET prefixo_ativo = 'OPU' WHERE nome = 'Opus Medical'"
                )
                rows = cur.rowcount
                print("     [OK] %d linha(s) atualizadas" % rows)
            except Exception as e:
                print("     [ERRO] %s" % str(e))
                return False

            # 2. Inicializar sequencia para Opus
            print("\n[2] Inicializando sequencia para Opus Medical...")
            try:
                cur.execute(
                    "INSERT INTO controle_ativos.sequencias_ativo (empresa_id, proximo_numero) "
                    "VALUES (1, 1) ON DUPLICATE KEY UPDATE empresa_id = empresa_id"
                )
                print("     [OK] Sequencia inicializada")
            except Exception as e:
                print("     [ERRO] %s" % str(e))
                return False

            # 3. Criar usuario teste em Vicente Martins
            print("\n[3] Criando usuario teste em Vicente Martins...")
            try:
                # Hash de "teste123"
                senha_hash = gerar_hash("teste123")

                resposta_hash = gerar_hash("Teste123")
                cur.execute(
                    "INSERT INTO controle_ativos.usuarios "
                    "(nome, email, senha_hash, pergunta_recuperacao, resposta_recuperacao_hash, empresa_id, perfil) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        "Usuario Teste VIC",
                        "teste_vic@example.com",
                        senha_hash,
                        "Qual eh seu gato favorito?",
                        resposta_hash,
                        2,  # Vicente Martins
                        "usuario"
                    )
                )
                user_id = cur.lastrowid
                print("     [OK] Usuario criado (id=%d)" % user_id)
            except Exception as e:
                if "Duplicate entry" in str(e):
                    print("     [AVISO] Usuario já existe")
                    # Pegar ID do usuario existente
                    cur.execute(
                        "SELECT id FROM controle_ativos.usuarios WHERE email = 'teste_vic@example.com'"
                    )
                    result = cur.fetchone()
                    if result:
                        user_id = result[0]
                        print("     [OK] Usando usuario existente (id=%d)" % user_id)
                else:
                    print("     [ERRO] %s" % str(e))
                    return False

            conn.commit()
            cur.close()

        print("\n" + "=" * 80)
        print("RESULTADO: [OK] Dados preparados para teste")
        print("=" * 80)
        print("\nProxima etapa: python scripts/validar_id_automatico.py")
        return True

    except Exception as e:
        print("\n[ERRO] %s" % str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = setup()
    sys.exit(0 if success else 1)
