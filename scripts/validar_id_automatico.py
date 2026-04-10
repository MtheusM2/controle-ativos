#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validacao Prática do ID Automatico

Testa:
1. Criacao de ativo e geração de ID
2. Incremento de ID
3. Separacao entre empresas
4. Quase simultaneidade (sem race condition)

Uso:
    python scripts/validar_id_automatico.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web_app.app import create_app
from models.ativos import Ativo
from services.ativos_service import AtivosService
from database.connection import cursor_mysql
from datetime import datetime
from threading import Thread

def get_empresas_com_prefixo():
    """
    Retorna empresas configuradas com prefixo.
    """
    with cursor_mysql() as (conn, cur):
        cur.execute(
            "SELECT id, nome, prefixo_ativo FROM empresas WHERE prefixo_ativo IS NOT NULL"
        )
        return cur.fetchall()

def get_usuarios_por_empresa(empresa_id):
    """
    Retorna primeiro usuario de uma empresa para testes.
    """
    with cursor_mysql() as (conn, cur):
        cur.execute(
            "SELECT id FROM usuarios WHERE empresa_id = %s LIMIT 1",
            (empresa_id,)
        )
        result = cur.fetchone()
        return result['id'] if result else None

def criar_ativo_teste(app, usuario_id, numero_teste):
    """
    Cria um ativo de teste e retorna ID gerado.
    Nota: empresa_id eh extraido do contexto do usuario, nao passado como param.
    """
    with app.app_context():
        ativos_service = AtivosService()

        data_hoje = datetime.now().strftime("%Y-%m-%d")
        ativo_data = Ativo(
            id_ativo="",  # Vazio - sera gerado
            tipo="Notebook",
            marca="Dell",
            modelo="Latitude 5520",
            usuario_responsavel="Teste %d" % numero_teste,
            departamento="TI",
            nota_fiscal="NF-%d" % numero_teste,
            garantia="12 meses",
            status="Em Uso",
            data_entrada=data_hoje,
            data_saida=None,
            criado_por="teste"
        )

        id_gerado = ativos_service.criar_ativo(ativo_data, usuario_id)
        return id_gerado

def validar_id_automatico():
    """
    Valida geração automatica de ID.
    """
    print("=" * 80)
    print("VALIDACAO DO ID AUTOMATICO - FASE C")
    print("=" * 80)

    try:
        app = create_app()

        # 1. Listar empresas com prefixo
        print("\n[1] Listando empresas com prefixo configurado...")
        empresas = get_empresas_com_prefixo()
        if not empresas:
            print("     [ERRO] Nenhuma empresa com prefixo configurado")
            return False

        for emp in empresas:
            print("     - Empresa %d: %s (prefixo=%s)" % (emp['id'], emp['nome'], emp['prefixo_ativo']))

        # 2. Testar criacao de ativo em primeira empresa
        print("\n[2] Testando criacao de ativo (primeiro)...")
        empresa_id = empresas[0]['id']
        usuario_id = get_usuarios_por_empresa(empresa_id)

        if not usuario_id:
            print("     [ERRO] Nenhum usuario encontrado para empresa %d" % empresa_id)
            return False

        print("     Usando empresa: %s (id=%d)" % (empresas[0]['nome'], empresa_id))
        print("     Usuario: id=%d" % usuario_id)

        id_1 = criar_ativo_teste(app, usuario_id, 1)
        print("     [OK] Primeiro ativo criado: %s" % id_1)

        # Validar formato
        prefixo_esperado = empresas[0]['prefixo_ativo']
        if id_1.startswith(prefixo_esperado + "-"):
            print("     [OK] Formato do ID correto (prefixo=%s)" % prefixo_esperado)
        else:
            print("     [ERRO] Formato do ID incorreto (esperado: %s-XXXXXX, recebido: %s)" % (prefixo_esperado, id_1))
            return False

        # 3. Testar incremento
        print("\n[3] Testando incremento de ID (segundo ativo mesma empresa)...")
        id_2 = criar_ativo_teste(app, usuario_id, 2)
        print("     [OK] Segundo ativo criado: %s" % id_2)

        # Extrair numeros
        num_1 = int(id_1.split("-")[1])
        num_2 = int(id_2.split("-")[1])

        if num_2 > num_1:
            print("     [OK] Incremento correto: %d -> %d" % (num_1, num_2))
        else:
            print("     [ERRO] Numeros nao incrementaram: %d, %d" % (num_1, num_2))
            return False

        # 4. Testar separacao entre empresas (se houver >1)
        if len(empresas) > 1:
            print("\n[4] Testando separacao entre empresas...")
            empresa2_id = empresas[1]['id']
            usuario2_id = get_usuarios_por_empresa(empresa2_id)

            if usuario2_id:
                id_empresa2 = criar_ativo_teste(app, usuario2_id, 3)
                print("     [OK] Ativo em empresa 2 criado: %s" % id_empresa2)

                prefixo2 = empresas[1]['prefixo_ativo']
                if id_empresa2.startswith(prefixo2 + "-"):
                    print("     [OK] Prefixo correto para empresa 2: %s" % prefixo2)
                else:
                    print("     [ERRO] Prefixo incorreto: %s" % id_empresa2)
                    return False

                # Verificar se sequencias sao independentes
                with cursor_mysql() as (conn, cur):
                    cur.execute(
                        "SELECT proximo_numero FROM sequencias_ativo WHERE empresa_id = %s",
                        (empresa_id,)
                    )
                    seq1 = cur.fetchone()['proximo_numero']

                    cur.execute(
                        "SELECT proximo_numero FROM sequencias_ativo WHERE empresa_id = %s",
                        (empresa2_id,)
                    )
                    seq2 = cur.fetchone()['proximo_numero']

                print("     - Proximos numeros: Empresa 1=%d, Empresa 2=%d" % (seq1, seq2))
                if seq1 > 1 and seq2 > 1:
                    print("     [OK] Sequencias independentes")
                else:
                    print("     [AVISO] Verificar logica de sequencias")
            else:
                print("     [AVISO] Nenhum usuario na empresa 2")
        else:
            print("\n[4] Pulando teste de multiplas empresas (apenas 1 disponivel)")

        # 5. Testar quase simultaneidade
        print("\n[5] Testando criacao concorrente (2 threads)...")
        ids_concorrentes = []

        def criar_em_thread(numero):
            id_criado = criar_ativo_teste(app, usuario_id, 100 + numero)
            ids_concorrentes.append(id_criado)

        thread1 = Thread(target=criar_em_thread, args=(1,))
        thread2 = Thread(target=criar_em_thread, args=(2,))

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        if len(ids_concorrentes) == 2:
            print("     [OK] Ambas as threads completaram")
            print("     - Thread 1: %s" % ids_concorrentes[0])
            print("     - Thread 2: %s" % ids_concorrentes[1])

            # Verificar se sao diferentes
            if ids_concorrentes[0] != ids_concorrentes[1]:
                print("     [OK] IDs diferentes (sem colisao)")
            else:
                print("     [ERRO] IDs identicos! Colisao detectada!")
                return False
        else:
            print("     [AVISO] Threads nao completaram corretamente")

        print("\n" + "=" * 80)
        print("RESULTADO: [OK] ID Automatico validado com sucesso")
        print("=" * 80)
        return True

    except Exception as e:
        print("\n[ERRO] %s" % str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = validar_id_automatico()
    sys.exit(0 if success else 1)
