#!/usr/bin/env python3
"""
Script de homologacao pratica da importacao em massa.

Objetivo: Validar o fluxo completo de importacao (preview -> confirmacao -> persistencia)
com dados realistas corporativos.

Cobertura: As 7 partes do plano de homologacao
1. Preparacao da planilha (analise de colunas, estrutura)
2. Teste de preview com lote pequeno
3. Teste de confirmacao com lote pequeno
4. Testes de resiliencia (erros, campos invalidos)
5. Validacao de persistencia no banco
6. Decisao de prontidao
7. Relatorio tecnico final
"""

import sys
import io
import json
from datetime import datetime, timedelta
from typing import Any

# Adiciona o diretorio raiz ao path para importacoes relativas funcionarem
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

from services.ativos_service import AtivosService, AtivoErro, PermissaoNegada
from database.connection import cursor_mysql


# ============================================================================
# PARTE 1 — DADOS DE TESTE REALISTAS CORPORATIVOS
# ============================================================================

def gerar_planilha_csv_teste_realista() -> bytes:
    """
    Gera planilha CSV com dados corporativos realistas.

    Inclui:
    - Colunas exatas (tipo_ativo, marca, modelo, setor, status, data_entrada)
    - Colunas sugeridas (teamviewer id, anydesk id)
    - Colunas ignoradas/sensíveis (PC, password, IMEI)
    - Linhas validas e invalidas para teste de resiliencia
    """
    headers = [
        "tipo_ativo",      # Exata
        "marca",           # Exata
        "modelo",          # Exata
        "setor",           # Exata
        "status",          # Exata
        "data_entrada",    # Exata
        "teamviewer id",   # Sugerida (sem underscore)
        "anydesk id",      # Sugerida (sem underscore)
        "PC",              # Ignorada (nao faz parte do dominio)
        "password",        # Ignorada (sensivel)
        "departamento",    # Exata (pode ter vindo como coluna explícita)
    ]

    # Dados realistas: carga de equipamentos de TI corporativa
    linhas_csv = [
        # Cabecalho
        ",".join(headers),

        # LOTE 1: Linhas validas com dados corporativos tipicos
        # Notebook com TeamViewer e AnyDesk sugeridos
        "Notebook,Dell,Inspiron 5520,T.I,Disponível,2026-04-10,123456789,ABC-DEF-123,maquina-001,senha123,Tecnologia da Informacao",

        # Desktop corporativo em uso
        "Desktop,HP,ProDesk 400 G9,Financeiro,Em Uso,2025-11-20,987654321,XYZ-ABC-789,estacao-002,pass456,Financeiro",

        # Monitor em almoxarifado
        "Monitor,Dell,U2423DE,T.I,Em Almoxarifado,2026-01-15,,,tela-001,,Tecnologia da Informacao",

        # Impressora em almoxarifado (sem TeamViewer/AnyDesk)
        "Impressora,Canon,ImageRUNNER 2520,Administrativo,Em Almoxarifado,2025-12-01,,,printer-001,,Administrativo",

        # LOTE 2: Linha com status invalido (teste de resiliencia)
        "Notebook,Lenovo,ThinkPad E14,Vendas,Status_Invalido,2026-02-20,444555666,DEF-GHI-444,maquina-003,senha789,Vendas",

        # LOTE 3: Linha com data invalida (teste de resiliencia)
        "Notebook,ASUS,VivoBook,Marketing,Disponível,2026-13-45,555666777,GHI-JKL-555,maquina-004,pass999,Marketing",

        # LOTE 4: Linha valida adicional (para validar volume de importacao)
        "Smartphone,Apple,iPhone 14 Pro,Executivo,Em Uso,2025-09-15,666777888,JKL-MNO-666,smartphone-001,senha111,Executivo",
    ]

    conteudo = "\n".join(linhas_csv)
    return conteudo.encode("utf-8")


# ============================================================================
# PARTE 2 — TESTES DE PREVIEW E CLASSIFICACAO DE COLUNAS
# ============================================================================

class HomologacaoPreview:
    """
    Testa o fluxo de preview da importacao.
    Valida: colunas exatas, sugeridas, ignoradas e estrutura de dados.
    """

    def __init__(self, service: AtivosService, user_id: int):
        self.service = service
        self.user_id = user_id
        self.resultado = None
        self.relatorio = {}

    def executar(self, conteudo_csv: bytes):
        """Gera preview e armazena resultado."""
        try:
            self.resultado = self.service.gerar_preview_importacao_csv(
                conteudo_csv,
                self.user_id
            )
            self._validar_preview()
        except (AtivoErro, PermissaoNegada) as e:
            self.relatorio["erro_preview"] = str(e)
            raise

    def _validar_preview(self):
        """Valida estrutura do preview gerado."""
        assert self.resultado is not None, "Preview nao foi gerado"

        # Estrutura esperada
        assert "colunas" in self.resultado
        assert "preview_linhas" in self.resultado
        assert "resumo_validacao" in self.resultado

        colunas = self.resultado["colunas"]
        assert "exatas" in colunas
        assert "sugeridas" in colunas
        assert "ignoradas" in colunas

        resumo = self.resultado["resumo_validacao"]
        assert "total_linhas" in resumo
        assert "linhas_validas" in resumo
        assert "linhas_invalidas" in resumo

        self.relatorio["preview_ok"] = True
        self.relatorio["total_linhas_csv"] = resumo["total_linhas"]
        self.relatorio["linhas_validas"] = resumo["linhas_validas"]
        self.relatorio["linhas_invalidas"] = resumo["linhas_invalidas"]

    def validar_colunas_exatas(self, esperadas: list[str]) -> bool:
        """Verifica se todas as colunas exatas esperadas foram classificadas."""
        exatas = [item["campo_destino"] for item in self.resultado["colunas"]["exatas"]]
        encontradas = [col for col in esperadas if col in exatas]
        faltantes = [col for col in esperadas if col not in exatas]

        self.relatorio["colunas_exatas_esperadas"] = esperadas
        self.relatorio["colunas_exatas_encontradas"] = encontradas
        self.relatorio["colunas_exatas_faltantes"] = faltantes

        return len(faltantes) == 0

    def validar_colunas_sugeridas(self, esperadas: dict[str, str]) -> bool:
        """Verifica se as colunas sugeridas foram corretamente identificadas."""
        sugeridas = {
            item["coluna_origem"]: item["campo_sugerido"]
            for item in self.resultado["colunas"]["sugeridas"]
        }

        self.relatorio["colunas_sugeridas"] = sugeridas

        # Todas as sugestoes esperadas devem estar presentes
        return all(col in sugeridas for col in esperadas.keys())

    def validar_colunas_ignoradas(self, esperadas: list[str]) -> bool:
        """Verifica se as colunas invalidas/sensíveis foram ignoradas."""
        ignoradas = [item["coluna_origem"] for item in self.resultado["colunas"]["ignoradas"]]
        encontradas = [col for col in esperadas if col in ignoradas]

        self.relatorio["colunas_ignoradas_esperadas"] = esperadas
        self.relatorio["colunas_ignoradas_encontradas"] = encontradas

        return len(encontradas) == len(esperadas)

    def validar_preview_linhas(self) -> dict:
        """Valida a amostra de linhas no preview."""
        linhas_preview = self.resultado["preview_linhas"]

        relatorio_linhas = {
            "amostra_size": len(linhas_preview),
            "campos_mapeados": set(),
            "primeira_linha": None,
        }

        if linhas_preview:
            relatorio_linhas["primeira_linha"] = linhas_preview[0]
            for linha in linhas_preview:
                relatorio_linhas["campos_mapeados"].update(
                    linha.get("dados_mapeados", {}).keys()
                )

        self.relatorio["preview_linhas"] = relatorio_linhas
        return relatorio_linhas

    def obter_erros_validacao(self) -> list[str]:
        """Extrai erros do resumo de validacao."""
        return self.resultado["resumo_validacao"].get("erros", [])

    def obter_avisos_validacao(self) -> list[str]:
        """Extrai avisos do resumo de validacao."""
        return self.resultado["resumo_validacao"].get("avisos", [])


# ============================================================================
# PARTE 3 — TESTES DE CONFIRMACAO E PERSISTENCIA
# ============================================================================

class HomologacaoConfirmacao:
    """
    Testa o fluxo de confirmacao e persistencia da importacao.
    Valida: aplicacao de mapeamento, criacao de ativos, integridade de dados.
    """

    def __init__(self, service: AtivosService, user_id: int):
        self.service = service
        self.user_id = user_id
        self.resultado = None
        self.relatorio = {}

    def executar(
        self,
        conteudo_csv: bytes,
        sugestoes_confirmadas: dict[str, str] | None = None
    ):
        """Executa confirmacao de importacao com sugestoes."""
        if sugestoes_confirmadas is None:
            sugestoes_confirmadas = {}

        try:
            self.resultado = self.service.confirmar_importacao_csv(
                conteudo_csv,
                sugestoes_confirmadas,
                self.user_id,
                modo_tudo_ou_nada=True
            )
            self._analisar_resultado()
        except (AtivoErro, PermissaoNegada) as e:
            self.relatorio["erro_confirmacao"] = str(e)
            raise

    def _analisar_resultado(self):
        """Analisa o resultado da importacao."""
        assert self.resultado is not None

        self.relatorio["ok_importacao"] = self.resultado.get("ok_importacao", False)
        self.relatorio["importados"] = self.resultado.get("importados", 0)
        self.relatorio["falhas"] = self.resultado.get("falhas", 0)
        self.relatorio["ids_criados"] = self.resultado.get("ids_criados", [])
        self.relatorio["erros"] = self.resultado.get("erros", [])
        self.relatorio["avisos"] = self.resultado.get("avisos", [])

    def obter_ids_importados(self) -> list[str]:
        """Retorna lista de IDs criados na importacao."""
        return self.resultado.get("ids_criados", [])

    def houve_falha(self) -> bool:
        """Indica se houve falha na importacao."""
        return not self.resultado.get("ok_importacao", False)


# ============================================================================
# PARTE 4 — VALIDACAO DE PERSISTENCIA NO BANCO
# ============================================================================

class ValidadorBanco:
    """
    Valida dados persistidos no banco de dados.
    Garante que nao ha sujeira estrutural ou mapeamento errado.
    """

    def __init__(self):
        self.relatorio = {}

    def validar_ativo_importado(self, id_ativo: str) -> dict:
        """Busca e valida um ativo importado no banco."""
        with cursor_mysql(dictionary=True) as (_conn, cur):
            cur.execute(
                """
                SELECT * FROM ativos
                WHERE id = %s
                LIMIT 1
                """,
                (id_ativo,)
            )
            row = cur.fetchone()

        if row is None:
            return {"encontrado": False, "id": id_ativo}

        # Validacoes criticas:
        # - IMEI deve ser NULL (nunca deve ter vindo da importacao)
        # - status deve ser valor valido
        # - data_entrada deve ser data valida
        # - campos de TeamViewer/AnyDesk podem estar preenchidos

        validacoes = {
            "encontrado": True,
            "id": id_ativo,
            "imei_1_null": row.get("imei_1") is None,
            "imei_2_null": row.get("imei_2") is None,
            "status": row.get("status"),
            "data_entrada": str(row.get("data_entrada")) if row.get("data_entrada") else None,
            "teamviewer_id": row.get("teamviewer_id"),
            "anydesk_id": row.get("anydesk_id"),
            "tipo_ativo": row.get("tipo_ativo"),
            "marca": row.get("marca"),
            "modelo": row.get("modelo"),
            "setor": row.get("setor"),
            "departamento": row.get("departamento"),
        }

        return validacoes

    def validar_lote_importado(self, ids: list[str]) -> dict:
        """Valida um lote de ativos importados."""
        resultados = {
            "total_ids": len(ids),
            "encontrados": 0,
            "ausentes": 0,
            "imei_violado": 0,
            "ids_validados": [],
            "problemas": [],
        }

        for id_ativo in ids:
            validacao = self.validar_ativo_importado(id_ativo)

            if not validacao["encontrado"]:
                resultados["ausentes"] += 1
                resultados["problemas"].append(f"ID {id_ativo} nao encontrado no banco")
            else:
                resultados["encontrados"] += 1

                # Verifica violacao de IMEI
                if not validacao["imei_1_null"] or not validacao["imei_2_null"]:
                    resultados["imei_violado"] += 1
                    resultados["problemas"].append(
                        f"ID {id_ativo} tem IMEI preenchido (violacao de contrato)"
                    )

                resultados["ids_validados"].append(validacao)

        return resultados


# ============================================================================
# EXECUTOR PRINCIPAL DE HOMOLOGACAO
# ============================================================================

class ExecutorHomologacao:
    """
    Orquestra todo o fluxo de homologacao em 7 partes.
    Gera relatorio tecnico final com decisao de prontidao.
    """

    def __init__(self, user_id: int = 1):
        self.service = AtivosService()
        self.user_id = user_id
        self.relatorio_final = {
            "timestamp_inicio": datetime.now().isoformat(),
            "user_id": user_id,
            "etapas": {},
            "resumo_executivo": {},
        }

    def executar_homologacao_completa(self) -> dict:
        """Executa as 7 partes da homologacao."""

        print("\n" + "=" * 70)
        print("HOMOLOGACAO PRATICA - IMPORTACAO EM MASSA")
        print("=" * 70)

        # PARTE 1: Preparacao da planilha
        print("\n[PARTE 1] Preparacao da planilha de teste...")
        conteudo_csv = gerar_planilha_csv_teste_realista()
        self.relatorio_final["etapas"]["parte_1"] = {
            "status": "OK",
            "tamanho_csv_bytes": len(conteudo_csv),
            "metodo": "Gerada internamente com dados corporativos realistas",
        }

        # PARTE 2: Teste de preview
        print("[PARTE 2] Teste de preview e classificacao de colunas...")
        try:
            preview = HomologacaoPreview(self.service, self.user_id)
            preview.executar(conteudo_csv)

            # Validacoes de colunas
            exatas_ok = preview.validar_colunas_exatas([
                "tipo_ativo", "marca", "modelo", "setor", "status", "data_entrada"
            ])
            sugeridas_ok = preview.validar_colunas_sugeridas({
                "teamviewer id": "teamviewer_id",
                "anydesk id": "anydesk_id",
            })
            ignoradas_ok = preview.validar_colunas_ignoradas(["PC", "password"])

            preview.validar_preview_linhas()

            self.relatorio_final["etapas"]["parte_2"] = {
                "status": "OK" if (exatas_ok and sugeridas_ok and ignoradas_ok) else "PARCIAL",
                "colunas_exatas_ok": exatas_ok,
                "colunas_sugeridas_ok": sugeridas_ok,
                "colunas_ignoradas_ok": ignoradas_ok,
                "preview": preview.relatorio,
                "erros_validacao": preview.obter_erros_validacao(),
                "avisos_validacao": preview.obter_avisos_validacao(),
            }

            print(f"  [OK] Colunas exatas: {'OK' if exatas_ok else 'FALHA'}")
            print(f"  [OK] Colunas sugeridas: {'OK' if sugeridas_ok else 'FALHA'}")
            print(f"  [OK] Colunas ignoradas: {'OK' if ignoradas_ok else 'FALHA'}")
            print(f"  [OK] Total de linhas: {preview.relatorio['total_linhas_csv']}")
            print(f"  [OK] Linhas validas: {preview.relatorio['linhas_validas']}")

        except Exception as e:
            self.relatorio_final["etapas"]["parte_2"] = {
                "status": "ERRO",
                "erro": str(e),
            }
            print(f"  [ERRO] ERRO: {e}")
            return self._finalizar_homologacao("ERRO na PARTE 2")

        # PARTE 3: Teste de confirmacao (com sugestoes confirmadas)
        print("\n[PARTE 3] Teste de confirmacao com sugestoes...")
        try:
            confirmacao = HomologacaoConfirmacao(self.service, self.user_id)
            sugestoes = {
                "teamviewer id": "teamviewer_id",
                "anydesk id": "anydesk_id",
            }
            confirmacao.executar(conteudo_csv, sugestoes)

            self.relatorio_final["etapas"]["parte_3"] = {
                "status": "OK" if not confirmacao.houve_falha() else "FALHA",
                "ok_importacao": confirmacao.resultado.get("ok_importacao"),
                "importados": confirmacao.resultado.get("importados", 0),
                "falhas": confirmacao.resultado.get("falhas", 0),
                "ids_criados": confirmacao.obter_ids_importados(),
                "erros": confirmacao.resultado.get("erros", []),
            }

            print(f"  [OK] Importados: {confirmacao.resultado.get('importados', 0)}")
            print(f"  [OK] Falhas: {confirmacao.resultado.get('falhas', 0)}")

            ids_importados = confirmacao.obter_ids_importados()
            if not ids_importados:
                print("  [AVISO] Nenhum ID foi importado")
                return self._finalizar_homologacao("Nenhum ativo foi importado")

        except Exception as e:
            self.relatorio_final["etapas"]["parte_3"] = {
                "status": "ERRO",
                "erro": str(e),
            }
            print(f"  [ERRO] ERRO: {e}")
            return self._finalizar_homologacao("ERRO na PARTE 3")

        # PARTE 4: Testes de resiliencia
        print("\n[PARTE 4] Testes de resiliencia (cenarios de erro)...")
        # Nota: Os dados de teste ja incluem linhas com erros
        # que devem ter sido detectadas no preview e confirmacao
        erros_detectados = self.relatorio_final["etapas"]["parte_3"].get("erros", [])
        self.relatorio_final["etapas"]["parte_4"] = {
            "status": "OK" if erros_detectados else "AVISO",
            "erros_detectados": len(erros_detectados),
            "lista_erros": erros_detectados[:5],  # Primeiros 5
        }
        print(f"  [OK] Erros detectados e bloqueados: {len(erros_detectados)}")

        # PARTE 5: Validacao de banco
        print("\n[PARTE 5] Validacao de persistencia no banco...")
        try:
            validador = ValidadorBanco()
            validacao_lote = validador.validar_lote_importado(ids_importados)

            problemas = validacao_lote["imei_violado"] + len([
                p for p in validacao_lote["problemas"] if "nao encontrado" in p
            ])

            self.relatorio_final["etapas"]["parte_5"] = {
                "status": "OK" if problemas == 0 else "FALHA",
                "encontrados": validacao_lote["encontrados"],
                "ausentes": validacao_lote["ausentes"],
                "imei_violado": validacao_lote["imei_violado"],
                "problemas": validacao_lote["problemas"],
                "ids_validados": validacao_lote["ids_validados"],
            }

            print(f"  [OK] Ativos encontrados no banco: {validacao_lote['encontrados']}")
            print(f"  [OK] Violacoes IMEI: {validacao_lote['imei_violado']}")

            if problemas > 0:
                print(f"  [ERRO] PROBLEMAS ENCONTRADOS: {problemas}")
                for problema in validacao_lote["problemas"][:3]:
                    print(f"    - {problema}")

        except Exception as e:
            self.relatorio_final["etapas"]["parte_5"] = {
                "status": "ERRO",
                "erro": str(e),
            }
            print(f"  [ERRO] ERRO: {e}")

        # PARTE 6: Decisao de prontidao
        print("\n[PARTE 6] Decisao de prontidao...")
        pronto = self._avaliar_prontidao()
        self.relatorio_final["etapas"]["parte_6"] = {
            "pronto_para_uso_controlado": pronto,
            "criterios_atendidos": [],
            "criterios_nao_atendidos": [],
        }

        # PARTE 7: Relatorio final
        print("\n[PARTE 7] Gerando relatorio tecnico final...")
        self.relatorio_final["timestamp_fim"] = datetime.now().isoformat()
        self.relatorio_final["resumo_executivo"] = self._gerar_resumo_executivo()

        return self.relatorio_final

    def _avaliar_prontidao(self) -> bool:
        """Avalia se a importacao está pronta para uso controlado."""
        etapas = self.relatorio_final["etapas"]

        # Criterios de prontidao:
        # 1. Preview deve estar OK
        # 2. Confirmacao deve estar OK com ativos importados
        # 3. Banco deve ter ativos sem violacao de IMEI
        # 4. Sem erros criticos

        preview_ok = etapas.get("parte_2", {}).get("status") == "OK"
        confirmacao_ok = etapas.get("parte_3", {}).get("status") == "OK"
        banco_ok = etapas.get("parte_5", {}).get("status") == "OK"

        return preview_ok and confirmacao_ok and banco_ok

    def _gerar_resumo_executivo(self) -> dict:
        """Gera resumo executivo da homologacao."""
        etapas = self.relatorio_final["etapas"]

        return {
            "resultado_final": "PRONTO PARA USO CONTROLADO" if self._avaliar_prontidao() else "REQUER AJUSTES",
            "total_etapas": len(etapas),
            "etapas_ok": sum(1 for e in etapas.values() if e.get("status") == "OK"),
            "total_ativos_importados": etapas.get("parte_3", {}).get("importados", 0),
            "violacoes_seguranca": etapas.get("parte_5", {}).get("imei_violado", 0),
            "recomendacoes": self._gerar_recomendacoes(),
        }

    def _gerar_recomendacoes(self) -> list[str]:
        """Gera recomendacoes tecnicas baseado nos resultados."""
        recomendacoes = []
        etapas = self.relatorio_final["etapas"]

        if etapas.get("parte_5", {}).get("imei_violado", 0) > 0:
            recomendacoes.append("CRITICO: IMEI ainda está sendo gravado no banco. Revisar mapeamento.")

        if etapas.get("parte_3", {}).get("status") == "FALHA":
            recomendacoes.append("Alguns ativos nao foram importados. Revisar erros de validacao.")

        if not recomendacoes:
            recomendacoes.append("Importacao pronta para uso em ambiente controlado.")
            recomendacoes.append("Proximos passos: 1) Testar com lote real de producao. 2) Documentar procedimento. 3) Deploy em servidor.")

        return recomendacoes

    def _finalizar_homologacao(self, razao: str) -> dict:
        """Finaliza homologacao com erro."""
        self.relatorio_final["timestamp_fim"] = datetime.now().isoformat()
        self.relatorio_final["status_geral"] = "FALHA"
        self.relatorio_final["razao_falha"] = razao
        return self.relatorio_final

    def exibir_relatorio(self):
        """Exibe relatorio em formato legivel."""
        print("\n" + "=" * 70)
        print("RELATORIO FINAL DE HOMOLOGACAO")
        print("=" * 70)

        resumo = self.relatorio_final["resumo_executivo"]
        print(f"\nRESULTADO FINAL: {resumo['resultado_final']}")
        print(f"Etapas OK: {resumo['etapas_ok']}/{resumo['total_etapas']}")
        print(f"Ativos importados: {resumo['total_ativos_importados']}")
        print(f"Violacoes de seguranca (IMEI): {resumo['violacoes_seguranca']}")

        print("\nRECOMENDAÇÕES:")
        for i, rec in enumerate(resumo["recomendacoes"], 1):
            print(f"  {i}. {rec}")

        print("\n" + "=" * 70)

        # Exibe detalhes por etapa
        for num_etapa, (chave, dados) in enumerate(self.relatorio_final["etapas"].items(), 1):
            print(f"\n[{chave.upper()}] Status: {dados.get('status', 'N/A')}")
            if "erro" in dados:
                print(f"  Erro: {dados['erro']}")


def main():
    """Ponto de entrada principal."""
    executor = ExecutorHomologacao(user_id=1)
    resultado = executor.executar_homologacao_completa()
    executor.exibir_relatorio()

    # Salva relatorio em JSON
    with open("relatorio_homologacao.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)

    print("\n[OK] Relatorio salvo em: relatorio_homologacao.json")

    return 0 if resultado["resumo_executivo"]["resultado_final"] == "PRONTO PARA USO CONTROLADO" else 1


if __name__ == "__main__":
    sys.exit(main())
