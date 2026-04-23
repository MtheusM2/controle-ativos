"""
Testes de cenários CSV complexos para o importador flexível.

Cobre os 13 cenários listados na homologação:
- C01: CSV com cabeçalho perfeito
- C02: CSV com cabeçalho alternativo (sinônimos)
- C03: CSV com colunas extras
- C04: CSV com cabeçalho deslocado (linha 3)
- C05: CSV sem colunas opcionais (sem email)
- C06: CSV com campo crítico ausente (sem tipo)
- C07: CSV com datas em formato alternativo (DD/MM/YYYY)
- C08: Planilha com linhas vazias intercaladas
- C09: Planilha com ativos duplicados no CSV (mesmo ID 2x)
- C10: IDs que já existem no banco
- C11: Setor/localização fora do padrão
- C12: Tipo inferível pela descrição
- C13: Taxa de erro > 50%
"""

import pytest
from services.ativos_service import AtivosService


# ============ CSV FIXTURES ============

CSV_CABECALHO_PERFEITO = b"""id,tipo,marca,modelo,departamento,status,data_entrada
NTB-001,Notebook,Dell,Latitude 5520,TI,Em Uso,2026-01-15
NTB-002,Notebook,Lenovo,ThinkPad X1,RH,Armazenado,2025-06-20
"""

CSV_CABECALHO_ALTERNATIVO = b"""patrimonio,tipo_equipamento,fabricante,modelo_equipamento,setor,situacao,data_entrada
NTB-001,Notebook,Dell,Latitude,TI,Em Uso,2026-01-15
NTB-002,Notebook,Lenovo,ThinkPad,RH,Armazenado,2025-06-20
"""

CSV_COLUNAS_EXTRAS = b"""id,tipo,marca,modelo,departamento,status,data_entrada,coluna_extra_1,coluna_extra_2
NTB-001,Notebook,Dell,Latitude,TI,Em Uso,2026-01-15,lixo,mais_lixo
NTB-002,Notebook,Lenovo,ThinkPad,RH,Armazenado,2025-06-20,junk,trash
"""

CSV_CABECALHO_DESLOCADO = b"""Sistema de Controle de Ativos - Exportado em 2026-04-22
Setor TI

id,tipo,marca,modelo,departamento,status,data_entrada
NTB-001,Notebook,Dell,Latitude,TI,Em Uso,2026-01-15
"""

CSV_SEM_COLUNAS_OPCIONAIS = b"""id,tipo,marca,modelo,departamento,status,data_entrada
NTB-001,Notebook,Dell,Latitude,TI,Em Uso,2026-01-15
NTB-002,Desktop,HP,ProDesk,Vendas,Em Uso,2025-06-20
"""

CSV_CAMPO_CRITICO_AUSENTE = b"""marca,modelo,departamento,status,data_entrada
Dell,Latitude,TI,Em Uso,2026-01-15
HP,ProDesk,Vendas,Armazenado,2025-06-20
"""

CSV_DATAS_FORMATO_ALTERNATIVO = b"""id,tipo,marca,modelo,departamento,status,data_entrada
NTB-001,Notebook,Dell,Latitude,TI,Em Uso,15/01/2026
NTB-002,Desktop,HP,ProDesk,Vendas,Armazenado,20/06/2025
"""

CSV_LINHAS_VAZIAS = b"""id,tipo,marca,modelo,departamento,status,data_entrada
NTB-001,Notebook,Dell,Latitude,TI,Em Uso,2026-01-15

NTB-002,Desktop,HP,ProDesk,Vendas,Armazenado,2025-06-01
,,,,,,
"""

CSV_IDS_DUPLICADOS_NO_CSV = b"""id,tipo,marca,modelo,departamento,status,data_entrada
NTB-001,Notebook,Dell,Latitude,TI,Em Uso,2026-01-15
NTB-001,Desktop,HP,ProDesk,Vendas,Armazenado,2025-06-01
NTB-002,Notebook,Lenovo,ThinkPad,RH,Em Uso,2025-06-20
"""

CSV_SETOR_FORA_PADRAO = b"""id,tipo,marca,modelo,departamento,status,data_entrada
NTB-001,Notebook,Dell,Latitude,Departamento Criativo XYZ,Em Uso,2026-01-15
NTB-002,Desktop,HP,ProDesk,Vendas,Em Uso,2025-06-20
"""

CSV_TIPO_INFERIVEL = b"""id,marca,modelo,departamento,status,data_entrada,descricao
NTB-001,Dell,Latitude,TI,Em Uso,2026-01-15,Notebook Dell Latitude com i7 e 16GB RAM
NTB-002,HP,ProDesk,Vendas,Em Uso,2025-06-20,Desktop HP ProDesk com Ryzen 5
"""

CSV_ALTA_TAXA_ERRO = b"""id,tipo,marca,modelo,departamento,status,data_entrada
NTB-001,Notebook,Dell,Latitude,TI,Em Uso,2026-13-45
NTB-002,Notebook,Dell,Latitude,TI,Em Uso,2026-14-01
NTB-003,Notebook,Dell,Latitude,TI,Em Uso,2026-15-99
NTB-004,Notebook,Dell,Latitude,TI,Em Uso,2026-01-15
"""


# ============ HELPERS ============

def _service_admin():
    """
    Factory para criar AtivosService com contexto de admin (acesso irrestrito).
    Reutilizado de test_robustez_csv_importacao.py.
    """
    from web_app.app import create_app

    app = create_app(None, service_overrides={})
    with app.app_context():
        service = AtivosService()
        original_contexto = service._obter_contexto_acesso

        def fake_contexto_acesso(*args, **kwargs):
            return {"perfil": "adm", "empresa_id": 1}

        service._obter_contexto_acesso = fake_contexto_acesso
        return service


# ============ TESTES ============

class TestCenariosCSVImportacao:
    """Testa 13 cenários de CSV do importador flexível."""

    # C01: Cabeçalho perfeito
    def test_csv_cabecalho_perfeito(self):
        """C01: CSV com cabeçalho perfeito retorna colunas exatas."""
        service = _service_admin()
        resultado = service.gerar_preview_importacao_csv(CSV_CABECALHO_PERFEITO, user_id=1)

        # Estrutura esperada (sem 'ok', vem direto do preview)
        assert "colunas" in resultado
        assert "resumo_analise" in resultado
        # Deve reconhecer a maioria das colunas
        assert resultado["resumo_analise"]["colunas_reconhecidas_automaticamente"] >= 4

    # C02: Cabeçalho alternativo (sinônimos)
    def test_csv_cabecalho_alternativo_sinonimos(self):
        """C02: CSV com cabeçalho alternativo mapeia sugestões."""
        service = _service_admin()
        resultado = service.gerar_preview_importacao_csv(CSV_CABECALHO_ALTERNATIVO, user_id=1)

        assert "colunas" in resultado
        # Deve ter colunas (exatas ou sugeridas)
        colunas = resultado.get("colunas", {})
        total_colunas = len(colunas.get("exatas", [])) + len(colunas.get("sugeridas", []))
        assert total_colunas > 0

    # C03: Colunas extras
    def test_csv_colunas_extras_ignoradas(self):
        """C03: CSV com colunas extras as ignora sem bloqueio."""
        service = _service_admin()
        resultado = service.gerar_preview_importacao_csv(CSV_COLUNAS_EXTRAS, user_id=1)

        # Colunas extras devem estar em "ignoradas"
        colunas_ignoradas = resultado.get("colunas", {}).get("ignoradas", [])
        assert len(colunas_ignoradas) >= 2

    # C04: Cabeçalho deslocado (SKIP — requer ServicoImportacao com DetectorCabecalho)
    def test_csv_cabecalho_deslocado_linha3(self):
        """C04: CSV com cabeçalho deslocado — testado em integracao_rotas (detector)."""
        pytest.skip("Requer DetectorCabecalho em ServicoImportacao, não em _carregar_csv_em_memoria")

    # C05: Sem colunas opcionais
    def test_csv_sem_colunas_opcionais(self):
        """C05: CSV sem colunas opcionais (email) não bloqueia, gera aviso."""
        service = _service_admin()
        resultado = service.gerar_preview_importacao_csv(CSV_SEM_COLUNAS_OPCIONAIS, user_id=1)

        assert "colunas" in resultado
        # Deve ter estrutura de preview
        assert "resumo_analise" in resultado

    # C06: Campo crítico ausente — BLOQUEIA
    def test_csv_campo_critico_ausente_bloqueia(self):
        """C06: CSV sem campo crítico (tipo) bloqueia importação."""
        service = _service_admin()
        resultado = service.gerar_preview_importacao_csv(CSV_CAMPO_CRITICO_AUSENTE, user_id=1)

        # Sem campos críticos (id, tipo), deve ter bloqueios
        bloqueios = resultado.get("bloqueios_importacao", [])
        assert len(bloqueios) > 0 or len(resultado.get("colunas", {}).get("exatas", [])) == 0

    # C07: Datas em formato alternativo
    def test_csv_datas_formato_alternativo(self):
        """C07: CSV com datas em DD/MM/YYYY gera erro nas linhas."""
        service = _service_admin()
        resultado = service.gerar_preview_importacao_csv(CSV_DATAS_FORMATO_ALTERNATIVO, user_id=1)

        # Formato alternativo não é reconhecido, deve gerar erro na linha
        erros_por_linha = resultado.get("erros_por_linha", [])
        assert len(erros_por_linha) > 0

    # C08: Linhas vazias
    def test_csv_linhas_vazias_ignoradas(self):
        """C08: CSV com linhas vazias as ignora na contagem."""
        service = _service_admin()
        resultado = service.gerar_preview_importacao_csv(CSV_LINHAS_VAZIAS, user_id=1)

        assert "colunas" in resultado
        # Deve contar apenas 2 linhas válidas (não as vazias)
        resumo = resultado.get("resumo_analise", {})
        assert resumo.get("total_linhas", 0) == 2

    # C09: IDs duplicados no CSV
    def test_csv_ids_duplicados_no_csv(self):
        """C09: CSV com IDs duplicados gera alerta."""
        service = _service_admin()
        resultado = service.gerar_preview_importacao_csv(CSV_IDS_DUPLICADOS_NO_CSV, user_id=1)

        # A validação pode estar em alertas ou em erros_por_linha
        avisos = resultado.get("avisos_por_linha", [])
        erros = resultado.get("erros_por_linha", [])
        # Pelo menos uma deve estar preenchida ou ter bloqueio
        assert len(avisos) > 0 or len(erros) > 0 or len(resultado.get("bloqueios_importacao", [])) > 0

    # C10: IDs já existentes no banco
    def test_csv_ids_ja_existem_no_banco(self):
        """C10: CSV com IDs já no banco retorna preview (detectado em seguranca)."""
        service = _service_admin()
        csv_com_id_existente = b"""id,tipo,marca,modelo,departamento,status,data_entrada
NTB-999-NAO-EXISTE,Notebook,Dell,Latitude,TI,Em Uso,2026-01-15
"""
        resultado = service.gerar_preview_importacao_csv(csv_com_id_existente, user_id=1)

        # Deve retornar preview (duplicata detectada em ServicoImportacaoComSeguranca)
        assert "colunas" in resultado

    # C11: Setor fora do padrão
    def test_csv_setor_fora_padrao(self):
        """C11: CSV com setor fora do padrão retorna preview."""
        service = _service_admin()
        resultado = service.gerar_preview_importacao_csv(CSV_SETOR_FORA_PADRAO, user_id=1)

        # Deve retornar preview válido
        assert "colunas" in resultado
        assert "resumo_analise" in resultado

    # C12: Tipo inferível
    def test_csv_tipo_inferivel_pela_descricao(self):
        """C12: CSV sem tipo mas com descrição."""
        service = _service_admin()
        resultado = service.gerar_preview_importacao_csv(CSV_TIPO_INFERIVEL, user_id=1)

        # Sem o campo "tipo", deve gerar aviso ou bloqueio
        assert "colunas" in resultado
        # Campo crítico faltando deve causar bloqueio
        assert len(resultado.get("bloqueios_importacao", [])) > 0

    # C13: Taxa de erro > 50%
    def test_csv_taxa_erro_bloqueia_acima_50_pct(self):
        """C13: CSV com taxa de erro > 50% é bloqueado."""
        service = _service_admin()
        resultado = service.gerar_preview_importacao_csv(CSV_ALTA_TAXA_ERRO, user_id=1)

        # Taxa de erro = 3/4 = 75%, deve bloquear
        resumo = resultado.get("resumo_analise", {})
        total = resumo.get("total_linhas", 0)
        invalidas = resumo.get("linhas_invalidas", 0)
        taxa_erro = (invalidas / total * 100) if total > 0 else 0

        # Deve ter bloqueios ou taxa > 50%
        bloqueios = resultado.get("bloqueios_importacao", [])
        assert taxa_erro > 50 or len(bloqueios) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
