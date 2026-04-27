"""
Test de round-trip: Exportação → Importação no mesmo sistema.

Garante que um CSV exportado pelo sistema pode ser reimportado sem perda de dados.
Este teste foi criado para evitar regressão no bug corrigido em 2026-04-27:
exportação usava campos alias ("tipo", "departamento") enquanto importação
esperava canônicos ("tipo_ativo", "setor"), causando falha 100% no preview.
"""

import pytest
import io
import csv
from services.ativos_service import AtivosService
from models.ativos import Ativo


class TestRoundTripExportacaoImportacao:
    """Testes de round-trip: exportar e reimportar ativos"""

    # NOTA: Teste de integração completa (service.gerar_preview_importacao_csv)
    # requer conexão ao banco. Veja conftest.py para fixtures que permitem rodar
    # testes com banco de teste isolado.
    # Os testes abaixo são testes unitários que não dependem do banco.

    @pytest.mark.skip(reason="Requer conexao ao banco MySQL. Testar manualmente via UI ou com fixtures de banco.")
    def test_exportacao_pode_ser_reimportada_no_preview(self):
        """
        Cenário crítico: CSV exportado deve ser aceito no preview de importação.

        Antes (BUG): Exportação gerava campos alias → Preview rejeitava 100% das linhas
        Depois (FIX): Exportação gera campos canônicos → Preview aceita

        NOTA: Este teste requer conexão ao banco. Use fixtures em conftest.py
        ou teste manualmente via UI do sistema.
        """
        # Simular dados de ativos a exportar
        # (Em produção, viriam do banco. Aqui usamos dados fake.)
        ativos = [
            Ativo(
                id_ativo="NTB-001",
                tipo="Notebook",
                tipo_ativo="Notebook",
                marca="Dell",
                modelo="Latitude 5530",
                serial="ABC123",
                codigo_interno="",
                descricao="Notebook de trabalho",
                categoria="Notebook",
                condicao="Bom",
                localizacao="",
                setor="Rh",
                departamento="Rh",
                usuario_responsavel="Joao Silva",
                email_responsavel="joao@example.com",
                nota_fiscal="NF-12345",
                garantia="24 meses",
                status="Disponível",
                data_entrada="2026-01-15",
                data_saida=None,
                data_compra=None,
                valor=None,
                observacoes=None,
                detalhes_tecnicos=None,
                processador=None,
                ram=None,
                armazenamento=None,
                sistema_operacional=None,
                carregador=None,
                teamviewer_id=None,
                anydesk_id=None,
                nome_equipamento=None,
                hostname=None,
                imei_1=None,
                imei_2=None,
                numero_linha=None,
                operadora=None,
                conta_vinculada=None,
                polegadas=None,
                resolucao=None,
                tipo_painel=None,
                entrada_video=None,
                fonte_ou_cabo=None,
                created_at=None,
                updated_at=None,
                data_ultima_movimentacao=None,
                criado_por="admin"
            ),
            Ativo(
                id_ativo="DKT-001",
                tipo="Desktop",
                tipo_ativo="Desktop",
                marca="Positivo",
                modelo="Positivo Master",
                serial="XYZ789",
                codigo_interno="",
                descricao="Desktop administrativo",
                categoria="Desktop",
                condicao="Bom",
                localizacao="",
                setor="Adm",
                departamento="Adm",
                usuario_responsavel="Maria Silva",
                email_responsavel="maria@example.com",
                nota_fiscal="NF-54321",
                garantia="12 meses",
                status="Em Uso",
                data_entrada="2026-02-20",
                data_saida=None,
                data_compra=None,
                valor=None,
                observacoes=None,
                detalhes_tecnicos=None,
                processador=None,
                ram=None,
                armazenamento=None,
                sistema_operacional=None,
                carregador=None,
                teamviewer_id=None,
                anydesk_id=None,
                nome_equipamento=None,
                hostname=None,
                imei_1=None,
                imei_2=None,
                numero_linha=None,
                operadora=None,
                conta_vinculada=None,
                polegadas=None,
                resolucao=None,
                tipo_painel=None,
                entrada_video=None,
                fonte_ou_cabo=None,
                created_at=None,
                updated_at=None,
                data_ultima_movimentacao=None,
                criado_por="admin"
            ),
        ]

        # Simular exportação (montando linhas como seria exportado)
        from web_app.routes.ativos_routes import _linhas_exportacao
        linhas_exportadas = _linhas_exportacao(ativos)

        # Validar que os campos exportados são canônicos
        assert all("tipo_ativo" in linha for linha in linhas_exportadas), \
            "Exportação deve conter campo 'tipo_ativo' (canônico, não alias 'tipo')"
        assert all("setor" in linha for linha in linhas_exportadas), \
            "Exportação deve conter campo 'setor' (canônico, não alias 'departamento')"
        assert all("tipo" not in linha for linha in linhas_exportadas), \
            "Exportação NÃO deve conter campo alias 'tipo'"
        assert all("departamento" not in linha for linha in linhas_exportadas), \
            "Exportação NÃO deve conter campo alias 'departamento'"

        # Montar CSV a partir das linhas exportadas
        output = io.StringIO()
        fieldnames = [
            "id", "tipo_ativo", "marca", "modelo", "usuario_responsavel",
            "setor", "status", "data_entrada", "data_saida",
            "nota_fiscal", "garantia"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for linha in linhas_exportadas:
            # Filtrar apenas os campos esperados
            linha_filtered = {k: v for k, v in linha.items() if k in fieldnames}
            writer.writerow(linha_filtered)

        csv_bytes = output.getvalue().encode("utf-8")

        # Tentar importar esse CSV via preview
        service = AtivosService()
        resultado = service.gerar_preview_importacao_csv(csv_bytes, user_id=1)

        # Validar que o preview aceita as linhas
        total = resultado["resumo_analise"]["total_linhas"]
        validas = resultado["resumo_analise"]["linhas_validas"]
        invalidas = resultado["resumo_analise"]["linhas_invalidas"]

        assert total > 0, "CSV deve ter linhas"
        assert validas > 0, f"CSV exportado deve ser válido no preview (encontrado {invalidas} inválidas de {total})"
        assert invalidas == 0, \
            f"Nenhuma linha deveria ser inválida no preview. Erros: {resultado['erros_por_linha']}"

    def test_status_exportados_sao_validos_na_importacao(self):
        """
        Status exportados pelo sistema devem ser reconhecidos na importação.
        """
        from utils.validators import STATUS_VALIDOS

        # Status que o sistema pode gerar na exportação
        status_teste = [
            "Disponível",
            "Em Uso",
            "Em Manutenção",
            "Reservado",
            "Baixado"
        ]

        for status in status_teste:
            assert status in STATUS_VALIDOS, \
                f"Status '{status}' deveria estar em STATUS_VALIDOS para validação de importação"

    def test_setores_exportados_sao_validos_na_importacao(self):
        """
        Setores exportados pelo sistema devem ser reconhecidos na importação.
        Normalização de valores deve transformar variações em valores canônicos.
        """
        from utils.validators import SETORES_VALIDOS
        from utils.normalizador_valores_importacao import normalizar_valor_setor

        # Setores que o sistema pode gerar na exportação
        setores_teste = ["T.I", "Rh", "Adm", "Financeiro", "Vendas"]

        for setor in setores_teste:
            assert setor in SETORES_VALIDOS, \
                f"Setor '{setor}' deveria estar em SETORES_VALIDOS"

            # Verificar que normalização não quebra valores válidos
            normalizado = normalizar_valor_setor(setor)
            assert normalizado in SETORES_VALIDOS or normalizado == setor, \
                f"Setor normalizado '{normalizado}' não está em SETORES_VALIDOS"

    def test_normalizacao_valores_funciona_corretamente(self):
        """
        Testa que a normalização de valores coloca valores alias no formato canônico.
        """
        from utils.normalizador_valores_importacao import normalizar_valor_setor

        casos_teste = [
            ("rh", "Rh"),      # Minúsculo → Title Case
            ("RH", "Rh"),      # Maiúsculo → Title Case
            ("adm", "Adm"),    # Minúsculo → Title Case
            ("ADM", "Adm"),    # Maiúsculo → Title Case
            ("Rh", "Rh"),      # Já é canônico → sem mudança
            ("t.i", "T.I"),    # Minúsculo com ponto → sem mudança no case mas reconhecido
            ("T.I", "T.I"),    # Já é canônico → sem mudança
        ]

        for entrada, esperado in casos_teste:
            resultado = normalizar_valor_setor(entrada)
            assert resultado == esperado, \
                f"normalizar_valor_setor('{entrada}') deveria retornar '{esperado}', " \
                f"mas retornou '{resultado}'"
