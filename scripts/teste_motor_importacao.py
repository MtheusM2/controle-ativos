#!/usr/bin/env python3
#
# scripts/teste_motor_importacao.py
#
# Script de teste rápido do novo motor de importação flexível.
# Valida que os componentes funcionam sem quebra.
#
# Uso:
#   python scripts/teste_motor_importacao.py
#

import sys
from pathlib import Path

# Adiciona raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.import_schema import (
    obter_campos_criticos,
    obter_sinonimo_campo,
    obter_sinonimo_valor,
    LIMIAR_CONFIANCA_ALTA,
)
from utils.import_header_detector import DetectorCabecalho
from utils.import_mapper import MotorMatching, ResultadoMatch
from services.importacao_service import ServicoImportacao


def teste_import_schema():
    """Testa módulo de schema."""
    print("\n" + "=" * 60)
    print("TESTE 1: import_schema.py")
    print("=" * 60)

    # Teste 1.1: Campos críticos
    campos_criticos = obter_campos_criticos()
    print(f"✓ Campos críticos ({len(campos_criticos)}):")
    print(f"  {sorted(campos_criticos)[:5]}... (e {len(campos_criticos) - 5} mais)")

    # Teste 1.2: Sinônimos de campo
    sinonimo = obter_sinonimo_campo("proprietario")
    assert sinonimo == "usuario_responsavel", f"Esperado 'usuario_responsavel', obteve {sinonimo}"
    print(f"✓ Sinônimo 'proprietario' → '{sinonimo}'")

    # Teste 1.3: Sinônimos de valor
    tipo_normalizado = obter_sinonimo_valor("tipos_ativo", "laptop")
    assert tipo_normalizado == "Notebook", f"Esperado 'Notebook', obteve {tipo_normalizado}"
    print(f"✓ Valor 'laptop' → '{tipo_normalizado}'")

    # Teste 1.4: Limiar de confiança
    print(f"✓ Limiar confiança alta: {LIMIAR_CONFIANCA_ALTA}%")

    print("\n✅ Testes de schema PASSARAM")


def teste_detector_cabecalho():
    """Testa detecção automática de cabeçalho."""
    print("\n" + "=" * 60)
    print("TESTE 2: import_header_detector.py")
    print("=" * 60)

    detector = DetectorCabecalho()

    # Teste 2.1: Cabeçalho na primeira linha (simples)
    linhas_simples = [
        "tipo_ativo,marca,modelo",
        "Notebook,Dell,XPS"
    ]
    numero, headers, score = detector.detectar_cabecalho(linhas_simples)
    print(f"✓ Detecção simples:")
    print(f"  Linha: {numero}, Score: {score:.0%}")
    print(f"  Headers: {headers}")

    # Teste 2.2: Cabeçalho com lixo acima
    linhas_com_lixo = [
        "PLANILHA DE ATIVOS",
        "",
        "tipo_ativo,marca,modelo",
        "Notebook,Dell,XPS"
    ]
    numero, headers, score = detector.detectar_cabecalho(linhas_com_lixo)
    assert numero == 2, f"Esperado linha 2, obteve {numero}"
    print(f"✓ Detecção com lixo:")
    print(f"  Linha detectada: {numero} (ignorou 2 linhas de lixo)")
    print(f"  Score: {score:.0%}")

    # Teste 2.3: Normalização manual
    headers_manual = detector.validar_cabecalho_manual("Tipo Ativo; Marca; Modelo", ";")
    assert len(headers_manual) == 3
    print(f"✓ Cabeçalho manual: {headers_manual}")

    print("\n✅ Testes de detecção PASSARAM")


def teste_motor_matching():
    """Testa matching de colunas com scores."""
    print("\n" + "=" * 60)
    print("TESTE 3: import_mapper.py")
    print("=" * 60)

    motor = MotorMatching()

    # Teste 3.1: Match exato
    matches = motor.processar_cabecalho(["tipo_ativo"])
    assert matches[0].campo_destino == "tipo_ativo"
    assert matches[0].score == 1.0
    print(f"✓ Match exato:")
    print(f"  'tipo_ativo' → '{matches[0].campo_destino}' (score={matches[0].score:.0%})")

    # Teste 3.2: Match por sinônimo
    matches = motor.processar_cabecalho(["proprietario"])
    assert matches[0].campo_destino == "usuario_responsavel"
    assert 0.90 <= matches[0].score <= 1.0
    print(f"✓ Match por sinônimo:")
    print(f"  'proprietario' → '{matches[0].campo_destino}' (score={matches[0].score:.0%}, estratégia={matches[0].estrategia})")

    # Teste 3.3: Match por similaridade
    matches = motor.processar_cabecalho(["tipo de ativo"])
    assert matches[0].campo_destino == "tipo_ativo"
    assert 0.60 <= matches[0].score < 1.0
    print(f"✓ Match por similaridade:")
    print(f"  'tipo de ativo' → '{matches[0].campo_destino}' (score={matches[0].score:.0%}, estratégia={matches[0].estrategia})")

    # Teste 3.4: Sem match (ignorado)
    matches = motor.processar_cabecalho(["xyz_coluna_aleatoria"])
    assert matches[0].campo_destino is None
    assert matches[0].score < 0.6
    print(f"✓ Sem match (ignorado):")
    print(f"  'xyz_coluna_aleatoria' → None (score={matches[0].score:.0%})")

    # Teste 3.5: Múltiplos campos
    headers = ["tipo_ativo", "proprietario", "data entrada"]
    matches = motor.processar_cabecalho(headers)
    print(f"✓ Processamento de múltiplos campos:")
    for match in matches:
        print(f"  '{match.coluna_origem}' → '{match.campo_destino}' ({match.score:.0%}, {match.estrategia})")

    print("\n✅ Testes de matching PASSARAM")


def teste_servico_importacao():
    """Testa orquestração do serviço."""
    print("\n" + "=" * 60)
    print("TESTE 4: importacao_service.py")
    print("=" * 60)

    servico = ServicoImportacao()

    # Teste 4.1: Parse de CSV simples
    csv_simples = "tipo_ativo,marca,modelo\nNotebook,Dell,XPS\n".encode("utf-8")
    headers, linhas, metadados = servico.processar_arquivo_csv(csv_simples)
    assert len(headers) == 3
    assert len(linhas) == 1
    print(f"✓ Parse CSV:")
    print(f"  Delimitador: '{metadados.delimitador}'")
    print(f"  Linhas: {len(linhas)}, Cabeçalho na linha: {metadados.numero_linha_cabecalho}")
    print(f"  Hash: {metadados.hash_arquivo[:16]}...")

    # Teste 4.2: Mapeamento
    resultado = servico.fazer_mapeamento(headers)
    print(f"✓ Mapeamento:")
    print(f"  Críticos mapeados: {resultado.campos_criticos_mapeados}")
    print(f"  Críticos faltantes: {resultado.campos_criticos_faltantes}")
    print(f"  Altos: {len(resultado.mapeamentos_altos)}, Médios: {len(resultado.mapeamentos_medios)}")

    # Teste 4.3: Preview estruturado
    preview = servico.gerar_preview_estruturado(resultado, linhas, max_linhas_preview=1)
    assert "colunas" in preview
    assert "exatas" in preview["colunas"]
    assert "resumo_validacao" in preview
    print(f"✓ Preview estruturado:")
    print(f"  Exatas: {len(preview['colunas']['exatas'])}")
    print(f"  Sugeridas: {len(preview['colunas']['sugeridas'])}")
    print(f"  Ignoradas: {len(preview['colunas']['ignoradas'])}")
    print(f"  Bloqueada: {preview['resumo_validacao']['bloqueada']}")

    print("\n✅ Testes de serviço PASSARAM")


def teste_casos_reais():
    """Testa cenários do mundo real."""
    print("\n" + "=" * 60)
    print("TESTE 5: Casos Reais")
    print("=" * 60)

    servico = ServicoImportacao()

    # Caso Real 1: CSV com variações de espaço/underscore
    csv_espacado = "Tipo De Ativo,Marca,Modelo\nNotebook,Dell,XPS\n".encode("utf-8")
    headers1, _, metadados1 = servico.processar_arquivo_csv(csv_espacado)
    resultado1 = servico.fazer_mapeamento(headers1)
    print(f"✓ Caso 1: Cabeçalho com espaços")
    print(f"  Faltantes: {resultado1.campos_criticos_faltantes}")

    # Caso Real 2: CSV com sinônimos
    csv_sinonimos = "Proprietário,Data Entrada,Marca,Modelo\nJoão,2026-04-20,Dell,XPS\n".encode("utf-8")
    headers2, _, _ = servico.processar_arquivo_csv(csv_sinonimos)
    matches2 = servico.motor_matching.processar_cabecalho(headers2)
    print(f"✓ Caso 2: Cabeçalho com sinônimos")
    for m in matches2:
        if m.campo_destino:
            print(f"  '{m.coluna_origem}' → '{m.campo_destino}' ({m.estrategia}, {m.score:.0%})")

    # Caso Real 3: CSV com cabeçalho em L2
    csv_lixo = "RELATÓRIO DE ATIVOS IMPORTADOS\n\nTipo De Ativo,Marca,Modelo\nNotebook,Dell,XPS\n".encode("utf-8")
    headers3, _, metadados3 = servico.processar_arquivo_csv(csv_lixo)
    print(f"✓ Caso 3: Cabeçalho em linha 2 (lixo acima)")
    print(f"  Detectado em linha: {metadados3.numero_linha_cabecalho}")
    print(f"  Score de detecção: {metadados3.score_deteccao_cabecalho:.0%}")

    print("\n✅ Testes de casos reais PASSARAM")


def main():
    """Executa todos os testes."""
    print("\n" + "🧪 TESTES DO MOTOR DE IMPORTAÇÃO FLEXÍVEL")
    print("=" * 60)

    try:
        teste_import_schema()
        teste_detector_cabecalho()
        teste_motor_matching()
        teste_servico_importacao()
        teste_casos_reais()

        print("\n" + "=" * 60)
        print("✅ TODOS OS TESTES PASSARAM")
        print("=" * 60)
        print("\nMotor está pronto para integração em ativos_service.py")
        print("Próximo passo: Atualizar gerar_preview_importacao_csv() para usar")
        print("ServicoImportacao ao invés de _classificar_colunas_importacao()")
        return 0

    except AssertionError as e:
        print(f"\n❌ ASSERTION FALHOU: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERRO: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
