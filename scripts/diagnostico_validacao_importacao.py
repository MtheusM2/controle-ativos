#!/usr/bin/env python3
"""
Diagnostico rapido dos erros de validacao na importacao.
Objetivo: Identificar exatamente quais linhas estao falhando e por quê.
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

from services.ativos_service import AtivosService, AtivoErro

def diag_preview():
    """Executa preview e mostra detalhes dos erros."""

    service = AtivosService()
    service._obter_contexto_acesso = lambda _user_id: {
        "perfil": "adm",
        "empresa_id": 1,
    }

    # CSV com linhas de teste
    csv_content = """tipo_ativo,marca,modelo,setor,status,data_entrada,teamviewer id,anydesk id,PC,password,departamento
Notebook,Dell,Inspiron 5520,T.I,Disponível,2026-04-10,123456789,ABC-DEF-123,maquina-001,senha123,Tecnologia da Informacao
Desktop,HP,ProDesk 400 G9,Financeiro,Em Uso,2025-11-20,987654321,XYZ-ABC-789,estacao-002,pass456,Financeiro
Monitor,Dell,U2423DE,T.I,Em Almoxarifado,2026-01-15,,,tela-001,,Tecnologia da Informacao
Impressora,Canon,ImageRUNNER 2520,Administrativo,Em Almoxarifado,2025-12-01,,,printer-001,,Administrativo
Notebook,Lenovo,ThinkPad E14,Vendas,Status_Invalido,2026-02-20,444555666,DEF-GHI-444,maquina-003,senha789,Vendas
Notebook,ASUS,VivoBook,Marketing,Disponível,2026-13-45,555666777,GHI-JKL-555,maquina-004,pass999,Marketing
Smartphone,Apple,iPhone 14 Pro,Executivo,Em Uso,2025-09-15,666777888,JKL-MNO-666,smartphone-001,senha111,Executivo"""

    conteudo_csv = csv_content.encode("utf-8")

    print("Executando preview...")
    resultado = service.gerar_preview_importacao_csv(conteudo_csv, user_id=1)

    print("\nRESUMO:")
    resumo = resultado["resumo_validacao"]
    print(f"Total de linhas: {resumo['total_linhas']}")
    print(f"Linhas validas: {resumo['linhas_validas']}")
    print(f"Linhas invalidas: {resumo['linhas_invalidas']}")

    print("\nERROS DETECTADOS:")
    for erro in resumo.get("erros", []):
        print(f"  - {erro}")

    print("\nAVISOS:")
    for aviso in resumo.get("avisos", []):
        print(f"  - {aviso}")

    print("\nCOLUNAS EXATAS:")
    for col in resultado["colunas"]["exatas"]:
        print(f"  - {col['coluna_origem']} -> {col['campo_destino']}")

    print("\nCOLUNAS SUGERIDAS:")
    for col in resultado["colunas"]["sugeridas"]:
        print(f"  - {col['coluna_origem']} -> {col['campo_sugerido']} ({col.get('motivo', 'similar')})")

    print("\nCOLUNAS IGNORADAS:")
    for col in resultado["colunas"]["ignoradas"]:
        print(f"  - {col['coluna_origem']} ({col.get('motivo', 'unknown')})")

    print("\nPREVIEW DAS LINHAS (AMOSTRA):")
    for linha in resultado["preview_linhas"][:3]:
        print(f"\n  Linha {linha['linha']}:")
        for campo, valor in linha.get("dados_mapeados", {}).items():
            print(f"    {campo}: {valor}")

if __name__ == "__main__":
    diag_preview()
