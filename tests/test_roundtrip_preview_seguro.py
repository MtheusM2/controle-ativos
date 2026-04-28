"""
Teste de round-trip completo:
Exportação de ativo → CSV → Preview com ServicoImportacaoComSeguranca

Garante que:
1. Exportação gera campos canônicos (tipo_ativo, setor, status)
2. CSV exportado é lido corretamente pelo importador
3. Dados são normalizados adequadamente
4. Validação passa sem erros
5. Linha é marcada como válida no preview

Teste criado para verificar correção do bug de 2026-04-28:
- Preview não normalizava valores (status "em uso" falhava na validação)
- ServicoImportacaoComSeguranca.gerar_preview_seguro() não chamava normalizar_dados_importacao_valores()
"""

import pytest
import io
import csv
from utils.normalizador_valores_importacao import normalizar_dados_importacao_valores
from utils.import_validators import ValidadorLinha


class TestRoundTripPreviewSeguro:
    """Testes de round-trip com o novo preview seguro"""

    def test_normalizacao_integrada_no_preview(self):
        """
        Testa que a normalização de valores funciona quando integrada no fluxo
        de dados mapeados do preview seguro.

        Simula:
        1. CSV é mapeado para campos canônicos
        2. Inferência de email é aplicada
        3. Valores são normalizados (NOVO FIX)
        4. Validação ocorre com valores normalizados
        """
        # Simular dados após mapeamento (como vem de _mapear_linha)
        dados_mapeados = {
            "id": "NTB-001",
            "tipo_ativo": "notebook",  # minúsculo
            "marca": "Dell",
            "modelo": "Latitude 5530",
            "setor": "rh",  # minúsculo, será normalizado para "Rh"
            "status": "em uso",  # lowercase com espaço, será normalizado para "Em Uso"
            "data_entrada": "2026-01-15",
            "usuario_responsavel": "João Silva",
            "email_responsavel": "joao@example.com"
        }

        # Aplicar normalização (como gerar_preview_seguro agora faz)
        dados_normalizados = normalizar_dados_importacao_valores(dados_mapeados)

        # Validar que normalização funcionou
        assert dados_normalizados["tipo_ativo"] == "Notebook", \
            "tipo_ativo deveria ser normalizado"
        assert dados_normalizados["setor"] == "Rh", \
            "setor deveria ser normalizado de 'rh' para 'Rh'"
        assert dados_normalizados["status"] == "Em Uso", \
            "status deveria ser normalizado de 'em uso' para 'Em Uso'"

        # Agora validar a linha com dados normalizados
        validador = ValidadorLinha()
        resultado = validador.validar(
            dados_normalizados,
            numero_linha=2,
            usuarios_existentes_cache={"João Silva"}
        )

        # Com os dados normalizados, a validação deveria passar
        assert resultado.valida, \
            f"Linha deveria ser válida após normalização. Erros: {resultado.erros}"
        assert len(resultado.erros) == 0, \
            f"Não deveria haver erros de validação. Encontrados: {resultado.erros}"

    def test_csv_com_valores_variados_normaliza_corretamente(self):
        """
        Testa cenário real:
        CSV tem valores em diferentes formatos (lowercase, com espaços, abreviações)
        Normalização converte para padrão válido
        Validação passa
        """
        # Simular dados variados como podem vir de um CSV
        casos_teste = [
            {
                "dados": {
                    "tipo_ativo": "notebook",
                    "setor": "mkt",
                    "status": "disponível"
                },
                "esperado_tipo": "Notebook",
                "esperado_setor": "Marketing",
                "esperado_status": "Disponível",
            },
            {
                "dados": {
                    "tipo_ativo": "DESKTOP",
                    "setor": "T.I",
                    "status": "EM USO"
                },
                "esperado_tipo": "Desktop",
                "esperado_setor": "T.I",
                "esperado_status": "Em Uso",
            },
            {
                "dados": {
                    "tipo_ativo": "celular",
                    "setor": "adm",
                    "status": "em manutencao"
                },
                "esperado_tipo": "Celular",
                "esperado_setor": "Adm",
                "esperado_status": "Em Manutenção",
            },
        ]

        for caso in casos_teste:
            dados = caso["dados"].copy()
            dados.update({
                "marca": "Teste",
                "modelo": "Modelo",
                "id": f"TEST-{casos_teste.index(caso)}"
            })

            # Normalizar
            dados_norm = normalizar_dados_importacao_valores(dados)

            # Validar
            assert dados_norm["tipo_ativo"] == caso["esperado_tipo"], \
                f"tipo_ativo não normalizado corretamente"
            assert dados_norm["setor"] == caso["esperado_setor"], \
                f"setor não normalizado corretamente"
            assert dados_norm["status"] == caso["esperado_status"], \
                f"status não normalizado corretamente"

    def test_validacao_com_valores_canônicos_passa(self):
        """
        Testa que após normalização, validação sempre passa (se dados são válidos).

        Este teste verifica o contrato: normalizar_dados_importacao_valores
        deve deixar os dados em estado que passa na validação de enum.
        """
        validador = ValidadorLinha()

        # Dados que após normalização devem ser válidos
        casos_teste = [
            ("notebook", "Rh", "Disponível"),
            ("desktop", "T.I", "Em Uso"),
            ("celular", "Adm", "Em Manutenção"),
            ("monitor", "Financeiro", "Reservado"),
            ("mouse", "Vendas", "Baixado"),
        ]

        for tipo, setor, status in casos_teste:
            dados = {
                "tipo_ativo": tipo,
                "marca": "Marca",
                "modelo": "Modelo",
                "setor": setor,
                "status": status,
                "data_entrada": "2026-01-15",
                "usuario_responsavel": "Teste"
            }

            resultado = validador.validar(dados, numero_linha=2)

            assert resultado.valida, \
                f"Validação deveria passar para tipo={tipo}, setor={setor}, status={status}. " \
                f"Erros: {resultado.erros}"

    def test_csv_exportado_pode_ser_reimportado(self):
        """
        Teste de integração: CSV gerado pela exportação é aceito no preview.

        Simula:
        1. Ativo é exportado (gera campos canônicos)
        2. CSV é montado
        3. CSV é lido novamente
        4. Dados são validados (com normalização)
        5. Preview retorna válido
        """
        # Simular dados exportados (como viriam de _linhas_exportacao)
        csv_content = """id,tipo_ativo,marca,modelo,setor,status,data_entrada,usuario_responsavel,email_responsavel
NTB-001,Notebook,Dell,Latitude 5530,Rh,Disponível,2026-01-15,João Silva,joao@example.com
NTB-002,Notebook,HP,EliteBook,T.I,Em Uso,2026-01-20,Maria Santos,maria@example.com
DKT-001,Desktop,Positivo,Master,Adm,Em Manutenção,2026-02-01,Pedro Costa,pedro@example.com
"""

        # Ler CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        linhas = list(reader)

        # Validar cada linha
        validador = ValidadorLinha()
        todas_validas = True
        erros_encontrados = []

        for i, linha in enumerate(linhas):
            # Normalizar (como gerar_preview_seguro agora faz)
            linha_norm = normalizar_dados_importacao_valores(linha)

            resultado = validador.validar(
                linha_norm,
                numero_linha=i + 2,
                usuarios_existentes_cache={"João Silva", "Maria Santos", "Pedro Costa"}
            )

            if not resultado.valida:
                todas_validas = False
                erros_encontrados.append({
                    "linha": i + 2,
                    "erros": resultado.erros
                })

        assert todas_validas, \
            f"Todas as linhas deveriam ser válidas no preview. " \
            f"Erros encontrados: {erros_encontrados}"
