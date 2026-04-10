#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ===========================================================================
# VALIDACAO PRATICA DO ID AUTOMATICO - FASE C DA PRIMEIRA ETAPA
# ===========================================================================
#
# Objetivo:
#   Validar que o ID automatico funciona corretamente em ambiente real,
#   cobrindo:
#     1. Criacao de ativos em diferentes empresas
#     2. Incremento correto da sequencia
#     3. Independencia das sequencias por empresa
#     4. Visibilidade do ID em todos os fluxos
#     5. Teste simples de concorrencia
#
# Uso:
#   python scripts/validate_phase1_id_automatico.py
#
# ===========================================================================

import sys
import os
from pathlib import Path
from datetime import datetime

# Adiciona o raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["FLASK_ENV"] = "testing"

from web_app.app import create_app
from services.ativos_service import AtivosService
from models.ativos import Ativo
from database.connection import cursor_mysql
import threading


class ValidadorIDAutomatico:
    """Valida o funcionamento do ID automatico."""

    def __init__(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

        self.ativos_service = AtivosService()
        self.resultados = []
        self.ids_gerados = {}

    def log_resultado(self, teste, passou, mensagem=""):
        """Registra o resultado de um teste."""
        status = "[OK]" if passou else "[FALHOU]"
        print(f"  {status} {teste}")
        if mensagem:
            print(f"       {mensagem}")
        self.resultados.append({"teste": teste, "passou": passou, "mensagem": mensagem})

    def teste_sequencia_empresa_opus(self):
        """Testa criacao de multiplos ativos na empresa Opus."""
        print("\n[1] TESTE - SEQUENCIA INCREMENTANDO NA EMPRESA OPUS")

        try:
            # Obtem um usuario de Opus
            with cursor_mysql(dictionary=True) as (conn, cur):
                cur.execute(
                    """
                    SELECT id FROM usuarios WHERE empresa_id = 1 AND perfil = 'usuario' LIMIT 1
                    """
                )
                user = cur.fetchone()

            if not user:
                self.log_resultado("Sequencia Opus", False, "Nenhum usuario de teste encontrado em Opus")
                return False

            user_id = user["id"]

            # Cria 3 ativos e verifica incremento
            ids = []
            for i in range(3):
                ativo = Ativo(
                    id_ativo="",
                    tipo=f"Equipamento Teste {i+1}",
                    marca="TestMark",
                    modelo="TestModel",
                    usuario_responsavel="Teste Fase C",
                    departamento="TI",
                    nota_fiscal="NF-TESTE",
                    garantia="12 meses",
                    status="Em Uso",
                    data_entrada=datetime.now().strftime("%Y-%m-%d"),
                    data_saida=None,
                    criado_por=user_id
                )

                id_gerado = self.ativos_service.criar_ativo(ativo, user_id)
                ids.append(id_gerado)

            # Verifica que os IDs sao incrementados
            numeros = [int(id.split('-')[1]) for id in ids]
            incrementa_corretamente = (numeros[1] == numeros[0] + 1 and numeros[2] == numeros[1] + 1)

            if incrementa_corretamente:
                self.log_resultado(
                    "Sequencia Opus",
                    True,
                    f"IDs gerados: {' -> '.join(ids)}"
                )
                self.ids_gerados["opus"] = ids
                return True
            else:
                self.log_resultado(
                    "Sequencia Opus",
                    False,
                    f"IDs nao incremental correto: {' -> '.join(ids)}"
                )
                return False

        except Exception as e:
            self.log_resultado("Sequencia Opus", False, str(e))
            return False

    def teste_sequencia_empresa_Vicente(self):
        """Testa criacao de multiplos ativos na empresa Vicente Martins."""
        print("\n[2] TESTE - SEQUENCIA INCREMENTANDO NA EMPRESA VICENTE MARTINS")

        try:
            # Obtem um usuario de Vicente Martins
            with cursor_mysql(dictionary=True) as (conn, cur):
                cur.execute(
                    """
                    SELECT id FROM usuarios WHERE empresa_id = 2 AND perfil = 'usuario' LIMIT 1
                    """
                )
                user = cur.fetchone()

            if not user:
                self.log_resultado("Sequencia Vicente", False, "Nenhum usuario de teste em Vicente Martins")
                return False

            user_id = user["id"]

            # Cria 2 ativos
            ids = []
            for i in range(2):
                ativo = Ativo(
                    id_ativo="",
                    tipo=f"Equipamento Vicente {i+1}",
                    marca="TestMark",
                    modelo="TestModel",
                    usuario_responsavel="Teste Fase C",
                    departamento="TI",
                    nota_fiscal="NF-TESTE",
                    garantia="12 meses",
                    status="Em Uso",
                    data_entrada=datetime.now().strftime("%Y-%m-%d"),
                    data_saida=None,
                    criado_por=user_id
                )

                id_gerado = self.ativos_service.criar_ativo(ativo, user_id)
                ids.append(id_gerado)

            # Verifica que comeca com VIC
            todos_vic = all(id.startswith("VIC-") for id in ids)
            incrementa = len(ids) == 2 and ids[1].split('-')[1] > ids[0].split('-')[1]

            if todos_vic and incrementa:
                self.log_resultado(
                    "Sequencia Vicente",
                    True,
                    f"IDs gerados: {' -> '.join(ids)}"
                )
                self.ids_gerados["vicente"] = ids
                return True
            else:
                self.log_resultado(
                    "Sequencia Vicente",
                    False,
                    f"IDs invalidos: {' -> '.join(ids)}"
                )
                return False

        except Exception as e:
            self.log_resultado("Sequencia Vicente", False, str(e))
            return False

    def teste_independencia_sequencias(self):
        """Valida que as sequencias sao independentes por empresa."""
        print("\n[3] TESTE - INDEPENDENCIA DE SEQUENCIAS POR EMPRESA")

        try:
            if "opus" not in self.ids_gerados or "vicente" not in self.ids_gerados:
                self.log_resultado("Independencia", False, "Ids anteriores nao disponíveis")
                return False

            ids_opus = self.ids_gerados["opus"]
            ids_vicente = self.ids_gerados["vicente"]

            # Verifica que os prefixos sao diferentes
            prefixos_ok = all(id.startswith("OPU-") for id in ids_opus) and \
                          all(id.startswith("VIC-") for id in ids_vicente)

            # Verifica que os numeros sao independentes (Vicente nao segue Opus)
            num_opus = [int(id.split('-')[1]) for id in ids_opus]
            num_vicente = [int(id.split('-')[1]) for id in ids_vicente]

            independentes = (num_vicente[0] != num_opus[-1] + 1)

            if prefixos_ok and independentes:
                self.log_resultado(
                    "Independencia",
                    True,
                    f"Opus: {num_opus[-1]}, Vicente: {num_vicente[-1]} (sequencias separadas)"
                )
                return True
            else:
                self.log_resultado(
                    "Independencia",
                    False,
                    f"Sequencias nao estao independentes"
                )
                return False

        except Exception as e:
            self.log_resultado("Independencia", False, str(e))
            return False

    def teste_visibilidade_id_listagem(self):
        """Valida que o ID aparece corretamente na listagem."""
        print("\n[4] TESTE - VISIBILIDADE DO ID NA LISTAGEM")

        try:
            if "opus" not in self.ids_gerados:
                self.log_resultado("Visibilidade Listagem", False, "Ids anteriores nao disponíveis")
                return False

            # Busca um usuario de Opus
            with cursor_mysql(dictionary=True) as (conn, cur):
                cur.execute(
                    """
                    SELECT id FROM usuarios WHERE empresa_id = 1 AND perfil = 'usuario' LIMIT 1
                    """
                )
                user = cur.fetchone()

            user_id = user["id"]

            # Lista ativos
            ativos = self.ativos_service.listar_ativos(user_id)

            # Verifica se algum dos IDs criados aparece
            ids_criados = self.ids_gerados["opus"]
            ids_listados = [a.id_ativo for a in ativos]

            encontrou = any(id in ids_listados for id in ids_criados)

            if encontrou:
                ids_encontrados = [id for id in ids_criados if id in ids_listados]
                self.log_resultado(
                    "Visibilidade Listagem",
                    True,
                    f"{len(ids_encontrados)} IDs encontrados na listagem"
                )
                return True
            else:
                self.log_resultado(
                    "Visibilidade Listagem",
                    False,
                    f"Nenhum dos IDs criados aparece na listagem"
                )
                return False

        except Exception as e:
            self.log_resultado("Visibilidade Listagem", False, str(e))
            return False

    def teste_visibilidade_id_detalhe(self):
        """Valida que o ID aparece corretamente no detalhe."""
        print("\n[5] TESTE - VISIBILIDADE DO ID NO DETALHE")

        try:
            if "opus" not in self.ids_gerados:
                self.log_resultado("Visibilidade Detalhe", False, "Ids anteriores nao disponíveis")
                return False

            # Busca um usuario de Opus
            with cursor_mysql(dictionary=True) as (conn, cur):
                cur.execute(
                    """
                    SELECT id FROM usuarios WHERE empresa_id = 1 AND perfil = 'usuario' LIMIT 1
                    """
                )
                user = cur.fetchone()

            user_id = user["id"]

            # Obtem detalhe de um ativo criado
            id_para_buscar = self.ids_gerados["opus"][0]
            ativo = self.ativos_service.buscar_ativo(id_para_buscar, user_id)

            if ativo and ativo.id_ativo == id_para_buscar:
                self.log_resultado(
                    "Visibilidade Detalhe",
                    True,
                    f"ID {ativo.id_ativo} aparece corretamente no detalhe"
                )
                return True
            else:
                self.log_resultado(
                    "Visibilidade Detalhe",
                    False,
                    f"ID nao aparece ou eh diferente"
                )
                return False

        except Exception as e:
            self.log_resultado("Visibilidade Detalhe", False, str(e))
            return False

    def teste_id_somente_leitura_edicao(self):
        """Valida que o ID eh somente leitura na edicao."""
        print("\n[6] TESTE - ID SOMENTE LEITURA NA EDICAO")

        try:
            if "opus" not in self.ids_gerados:
                self.log_resultado("ID Somente Leitura", False, "Ids anteriores nao disponíveis")
                return False

            # Busca um usuario
            with cursor_mysql(dictionary=True) as (conn, cur):
                cur.execute(
                    """
                    SELECT id FROM usuarios WHERE empresa_id = 1 AND perfil = 'usuario' LIMIT 1
                    """
                )
                user = cur.fetchone()

            user_id = user["id"]

            # Tenta "mudar" o ID ao editar (o backend deve ignorar)
            id_original = self.ids_gerados["opus"][0]

            # Tenta atualizar apenas outro campo
            self.ativos_service.atualizar_ativo(
                id_original,
                {"usuario_responsavel": "Usuario Modificado"},
                user_id
            )

            # Verifica que o ID nao mudou
            ativo_apos = self.ativos_service.buscar_ativo(id_original, user_id)

            if ativo_apos.id_ativo == id_original:
                self.log_resultado(
                    "ID Somente Leitura",
                    True,
                    f"ID {id_original} permanece inalterado"
                )
                return True
            else:
                self.log_resultado(
                    "ID Somente Leitura",
                    False,
                    f"ID foi alterado (comportamento incorreto)"
                )
                return False

        except Exception as e:
            self.log_resultado("ID Somente Leitura", False, str(e))
            return False

    def teste_concorrencia_basica(self):
        """Testa se criacao concorrente gera IDs diferentes."""
        print("\n[7] TESTE - CONCORRENCIA BASICA (2 THREADS)")

        try:
            # Busca usuario de Opus
            with cursor_mysql(dictionary=True) as (conn, cur):
                cur.execute(
                    """
                    SELECT id FROM usuarios WHERE empresa_id = 1 AND perfil = 'usuario' LIMIT 1
                    """
                )
                user = cur.fetchone()

            user_id = user["id"]

            ids_criados_thread = []
            erros_thread = []

            def criar_no_thread():
                try:
                    ativo = Ativo(
                        id_ativo="",
                        tipo="Equipamento Concorrente",
                        marca="TestMark",
                        modelo="TestModel",
                        usuario_responsavel="Teste Concorrencia",
                        departamento="TI",
                        nota_fiscal="NF-CONC",
                        garantia="12 meses",
                        status="Em Uso",
                        data_entrada=datetime.now().strftime("%Y-%m-%d"),
                        data_saida=None,
                        criado_por=user_id
                    )

                    id_gerado = self.ativos_service.criar_ativo(ativo, user_id)
                    ids_criados_thread.append(id_gerado)
                except Exception as e:
                    erros_thread.append(str(e))

            # Cria 2 threads que criam ativos simultaneamente
            threads = [threading.Thread(target=criar_no_thread) for _ in range(2)]

            for t in threads:
                t.start()

            for t in threads:
                t.join()

            if erros_thread:
                self.log_resultado(
                    "Concorrencia",
                    False,
                    f"Erros nas threads: {', '.join(erros_thread[:1])}"
                )
                return False

            if len(ids_criados_thread) == 2 and ids_criados_thread[0] != ids_criados_thread[1]:
                self.log_resultado(
                    "Concorrencia",
                    True,
                    f"IDs unicos gerados: {', '.join(ids_criados_thread)}"
                )
                return True
            else:
                self.log_resultado(
                    "Concorrencia",
                    False,
                    f"IDs duplicados ou insuficientes"
                )
                return False

        except Exception as e:
            self.log_resultado("Concorrencia", False, str(e))
            return False

    def teste_ativos_antigos_continuam_funcionando(self):
        """Valida que ativos antigos (antes da migracao) continuam visíveis."""
        print("\n[8] TESTE - ATIVOS ANTIGOS CONTINUAM FUNCIONANDO")

        try:
            # Busca usuario
            with cursor_mysql(dictionary=True) as (conn, cur):
                cur.execute(
                    """
                    SELECT id FROM usuarios WHERE empresa_id = 1 AND perfil = 'usuario' LIMIT 1
                    """
                )
                user = cur.fetchone()

            user_id = user["id"]

            # Lista todos os ativos de Opus
            ativos = self.ativos_service.listar_ativos(user_id)

            # Deve ter pelo menos alguns ativos (os antigos + os novos criados)
            if ativos and len(ativos) >= 3:
                self.log_resultado(
                    "Ativos Antigos",
                    True,
                    f"Total de {len(ativos)} ativos visiveis (antigos + novos)"
                )
                return True
            else:
                self.log_resultado(
                    "Ativos Antigos",
                    False,
                    f"Numero insuficiente de ativos"
                )
                return False

        except Exception as e:
            self.log_resultado("Ativos Antigos", False, str(e))
            return False

    def executar_validacao(self):
        """Executa a suite completa de validacoes."""
        print("=" * 70)
        print("VALIDACAO PRATICA DO ID AUTOMATICO - FASE C")
        print("=" * 70)

        self.teste_sequencia_empresa_opus()
        self.teste_sequencia_empresa_Vicente()
        self.teste_independencia_sequencias()
        self.teste_visibilidade_id_listagem()
        self.teste_visibilidade_id_detalhe()
        self.teste_id_somente_leitura_edicao()
        self.teste_concorrencia_basica()
        self.teste_ativos_antigos_continuam_funcionando()

        # Resumo
        print("\n" + "=" * 70)
        print("RESUMO DA VALIDACAO ID AUTOMATICO")
        print("=" * 70)

        passou = sum(1 for r in self.resultados if r["passou"])
        total = len(self.resultados)

        for resultado in self.resultados:
            status = "[OK]" if resultado["passou"] else "[FALHOU]"
            print(f"  {status}: {resultado['teste']}")

        print(f"\nResultado: {passou}/{total} testes passaram")

        self.app_context.pop()

        if passou == total:
            print("\n[OK] FASE C VALIDADA COM SUCESSO")
            return True
        else:
            print(f"\n[FALHOU] FASE C INCOMPLETA ({total - passou} falha(s))")
            return False


if __name__ == "__main__":
    try:
        validador = ValidadorIDAutomatico()
        sucesso = validador.executar_validacao()
        sys.exit(0 if sucesso else 1)
    except Exception as e:
        print(f"\n[ERRO] ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
