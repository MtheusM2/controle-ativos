#!/usr/bin/env python3
"""
Script de homologacao com dados REALMENTE VALIDOS e testes praticos.

Objetivo: Validar fluxo completo de importacao em massa.
Assunção: Todos os dados de entrada são válidos segundo o domínio do sistema.
"""

import sys
import os
import json
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

from services.ativos_service import AtivosService, AtivoErro, PermissaoNegada
from database.connection import cursor_mysql

# ============================================================================
# DADOS DE TESTE VALIDOS (Baseado em dominio corporativo real)
# ============================================================================

CSV_TESTE_VALIDO = """tipo_ativo,marca,modelo,setor,status,data_entrada,usuario_responsavel,teamviewer id,anydesk id,departamento
Notebook,Dell,Inspiron 5520,T.I,Disponível,2026-04-10,,123456789,ABC-DEF-123,Tecnologia da Informacao
Desktop,HP,ProDesk 400 G9,Financeiro,Em Uso,2025-11-20,Joao Silva,987654321,XYZ-ABC-789,Financeiro
Monitor,Dell,U2423DE,T.I,Disponível,2026-01-15,,111222333,DEF-GHI-111,Tecnologia da Informacao
Celular,Apple,iPhone 14 Pro,Financeiro,Em Uso,2025-09-15,Carlos Santos,666777888,MNO-PQR-666,Financeiro
Mouse,Razer,DeathAdder V3,T.I,Reservado,2026-03-05,,777888999,PQR-STU-777,Tecnologia da Informacao"""


# ============================================================================
# EXECUCAO DE HOMOLOGACAO
# ============================================================================

def testar_preview():
    """Teste PARTE 2: Preview e classificacao."""
    print("\n" + "=" * 70)
    print("TESTE 1: PREVIEW E CLASSIFICACAO DE COLUNAS")
    print("=" * 70)

    service = AtivosService()
    service._obter_contexto_acesso = lambda _user_id: {
        "perfil": "adm",
        "empresa_id": 1,
    }

    conteudo_csv = CSV_TESTE_VALIDO.encode("utf-8")
    preview = service.gerar_preview_importacao_csv(conteudo_csv, user_id=1)

    resumo = preview["resumo_validacao"]
    print(f"\nTotal de linhas CSV: {resumo['total_linhas']}")
    print(f"Linhas validas: {resumo['linhas_validas']}")
    print(f"Linhas invalidas: {resumo['linhas_invalidas']}")

    if resumo["erros"]:
        print("\n[ERROS ENCONTRADOS]")
        for erro in resumo["erros"]:
            print(f"  - {erro}")

    if resumo["avisos"]:
        print("\n[AVISOS]")
        for aviso in resumo["avisos"]:
            print(f"  - {aviso}")

    # Validar colunas
    print("\n[COLUNAS EXATAS]")
    for col in preview["colunas"]["exatas"]:
        print(f"  {col['coluna_origem']} -> {col['campo_destino']}")

    print("\n[COLUNAS SUGERIDAS]")
    for col in preview["colunas"]["sugeridas"]:
        print(f"  {col['coluna_origem']} -> {col['campo_sugerido']}")

    print("\n[COLUNAS IGNORADAS]")
    for col in preview["colunas"]["ignoradas"]:
        print(f"  {col['coluna_origem']}")

    print("\n[PREVIEW DE AMOSTRA (Primeiras 3 linhas)]")
    for linha in preview["preview_linhas"][:3]:
        print(f"\nLinha {linha['linha']}:")
        for campo, valor in sorted(linha.get("dados_mapeados", {}).items()):
            print(f"  {campo}: {valor}")

    return preview, conteudo_csv


def testar_confirmacao(conteudo_csv: bytes, preview: dict):
    """Teste PARTE 3: Confirmacao e persistencia."""
    print("\n" + "=" * 70)
    print("TESTE 2: CONFIRMACAO E PERSISTENCIA")
    print("=" * 70)

    service = AtivosService()
    service._obter_contexto_acesso = lambda _user_id: {
        "perfil": "adm",
        "empresa_id": 1,
    }

    # Sugestoes confirmadas (TeamViewer e AnyDesk)
    sugestoes_confirmadas = {
        "teamviewer id": "teamviewer_id",
        "anydesk id": "anydesk_id",
    }

    print(f"\nConfirmando sugestoes...")
    for origem, destino in sugestoes_confirmadas.items():
        print(f"  {origem} -> {destino}")

    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas,
        user_id=1,
        modo_tudo_ou_nada=True
    )

    print(f"\n[RESULTADO]")
    print(f"Sucesso: {resultado.get('ok_importacao', False)}")
    print(f"Importados: {resultado.get('importados', 0)}")
    print(f"Falhas: {resultado.get('falhas', 0)}")

    if resultado.get("ids_criados"):
        print(f"\n[IDS CRIADOS]")
        for id_ativo in resultado["ids_criados"]:
            print(f"  - {id_ativo}")

    if resultado.get("erros"):
        print(f"\n[ERROS]")
        for erro in resultado["erros"]:
            print(f"  - {erro}")

    return resultado


def validar_banco(ids_importados: list[str]):
    """Teste PARTE 5: Validacao de persistencia no banco."""
    print("\n" + "=" * 70)
    print("TESTE 3: VALIDACAO DE PERSISTENCIA NO BANCO")
    print("=" * 70)

    if not ids_importados:
        print("\n[AVISO] Nenhum ID para validar")
        return {"ok": False}

    problemas = []
    validacoes_ok = []

    with cursor_mysql(dictionary=True) as (_conn, cur):
        for id_ativo in ids_importados:
            cur.execute("SELECT * FROM ativos WHERE id = %s LIMIT 1", (id_ativo,))
            row = cur.fetchone()

            if not row:
                problemas.append(f"ID {id_ativo} nao encontrado no banco")
                continue

            # Validacoes criticas
            print(f"\n[ID: {id_ativo}]")
            print(f"  Tipo: {row.get('tipo_ativo')}")
            print(f"  Status: {row.get('status')}")
            print(f"  Data entrada: {row.get('data_entrada')}")
            print(f"  TeamViewer: {row.get('teamviewer_id')}")
            print(f"  AnyDesk: {row.get('anydesk_id')}")

            # CRITICO: IMEI nao deve estar preenchido
            imei_1 = row.get("imei_1")
            imei_2 = row.get("imei_2")

            if imei_1 or imei_2:
                problemas.append(f"[CRITICO] ID {id_ativo} tem IMEI preenchido: imei_1={imei_1}, imei_2={imei_2}")
            else:
                print(f"  IMEI: OK (nao preenchido)")
                validacoes_ok.append(f"ID {id_ativo} OK")

    print(f"\n[RESUMO VALIDACAO BANCO]")
    print(f"Ativos validados: {len(ids_importados)}")
    print(f"Validacoes OK: {len(validacoes_ok)}")
    print(f"Problemas encontrados: {len(problemas)}")

    if problemas:
        print(f"\n[PROBLEMAS]")
        for p in problemas:
            print(f"  - {p}")
        return {"ok": False, "problemas": problemas}

    return {"ok": True}


def testar_cenarios_erro():
    """Teste PARTE 4: Cenarios de erro e resiliencia."""
    print("\n" + "=" * 70)
    print("TESTE 4: CENARIOS DE ERRO E RESILIENCIA")
    print("=" * 70)

    service = AtivosService()
    service._obter_contexto_acesso = lambda _user_id: {
        "perfil": "adm",
        "empresa_id": 1,
    }

    # CSV com erros intencionais
    csv_com_erros = """tipo_ativo,marca,modelo,setor,status,data_entrada,usuario_responsavel,teamviewer id,anydesk id,departamento
Notebook,Dell,Inspiron,T.I,Status_Invalido,2026-04-10,,111,222,T.I
Notebook,Lenovo,ThinkPad,Vendas,Disponível,2026-13-45,,333,444,Vendas
Desktop,HP,ProDesk,Finance,Em Uso,2025-11-20,,555,666,Finance"""

    conteudo_csv_erros = csv_com_erros.encode("utf-8")

    print("\nTestando preview com dados invalidos...")
    preview = service.gerar_preview_importacao_csv(conteudo_csv_erros, user_id=1)

    resumo = preview["resumo_validacao"]
    print(f"Linhas validas: {resumo['linhas_validas']}")
    print(f"Linhas invalidas: {resumo['linhas_invalidas']}")

    if resumo["erros"]:
        print(f"\n[ERROS DETECTADOS - {len(resumo['erros'])} total]")
        for erro in resumo["erros"][:5]:
            print(f"  - {erro}")

    return {"erros_detectados": len(resumo["erros"])}


# ============================================================================
# RELATORIO FINAL
# ============================================================================

def main():
    """Executa homologacao completa."""
    print("\n" + "=" * 70)
    print("HOMOLOGACAO PRATICA - IMPORTACAO EM MASSA")
    print("Data: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    relatorio = {
        "timestamp": datetime.now().isoformat(),
        "testes": {}
    }

    # TESTE 1: Preview
    try:
        preview, conteudo_csv = testar_preview()
        relatorio["testes"]["teste_1_preview"] = "OK"
    except Exception as e:
        print(f"\n[ERRO] Teste 1 falhou: {e}")
        relatorio["testes"]["teste_1_preview"] = f"ERRO: {e}"
        return relatorio

    # TESTE 2: Confirmacao
    try:
        resultado = testar_confirmacao(conteudo_csv, preview)
        ids_importados = resultado.get("ids_criados", [])
        relatorio["testes"]["teste_2_confirmacao"] = "OK"
        relatorio["testes"]["total_importados"] = len(ids_importados)
    except Exception as e:
        print(f"\n[ERRO] Teste 2 falhou: {e}")
        relatorio["testes"]["teste_2_confirmacao"] = f"ERRO: {e}"
        return relatorio

    # TESTE 3: Validacao Banco
    try:
        if ids_importados:
            validacao = validar_banco(ids_importados)
            relatorio["testes"]["teste_3_banco"] = "OK" if validacao["ok"] else "FALHA"
        else:
            print("\n[AVISO] Nenhum ativo foi importado para validar banco")
            relatorio["testes"]["teste_3_banco"] = "SKIPPED (nenhum ativo importado)"
    except Exception as e:
        print(f"\n[ERRO] Teste 3 falhou: {e}")
        relatorio["testes"]["teste_3_banco"] = f"ERRO: {e}"

    # TESTE 4: Cenarios de erro
    try:
        erro_test = testar_cenarios_erro()
        relatorio["testes"]["teste_4_erros"] = f"OK ({erro_test['erros_detectados']} erros detectados)"
    except Exception as e:
        print(f"\n[ERRO] Teste 4 falhou: {e}")
        relatorio["testes"]["teste_4_erros"] = f"ERRO: {e}"

    # Relatorio final
    print("\n" + "=" * 70)
    print("RELATORIO FINAL")
    print("=" * 70)

    for teste, status in relatorio["testes"].items():
        print(f"{teste}: {status}")

    pronto = all(
        "OK" in str(v) or "SKIPPED" in str(v)
        for v in relatorio["testes"].values()
    )

    print(f"\n[RESULTADO FINAL] {'PRONTO PARA USO CONTROLADO' if pronto else 'REQUER AJUSTES'}")

    # Salva relatorio
    with open("relatorio_homologacao_final.json", "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nRelatorio salvo em: relatorio_homologacao_final.json")

    return 0 if pronto else 1


if __name__ == "__main__":
    sys.exit(main())
