"""
Testes dos validadores de importação.

Cobre:
- ValidadorCampos (tipo, comprimento, enum, datas, emails)
- ValidadorLinha (validação de linha completa)
- ValidadorLote (validação de lote + bloqueios)
"""

import pytest
from utils.import_validators import (
    ValidadorCampos,
    ValidadorLinha,
    ValidadorLote,
    TipoErro,
    TipoAviso,
    classificar_status_importacao
)


class TestValidadorCampos:
    """Testa validação de campos individuais"""

    def test_id_valido(self):
        """ID válido não retorna erro"""
        resultado = ValidadorCampos.validar_id("NTB-001")
        assert resultado is None

    def test_id_muito_longo(self):
        """ID com mais de 20 caracteres retorna erro"""
        resultado = ValidadorCampos.validar_id("A" * 25)
        assert resultado is not None
        assert resultado[0] == TipoErro.VALOR_EXCEDE_COMPRIMENTO

    def test_id_caracteres_invalidos(self):
        """ID com caracteres especiais retorna erro"""
        resultado = ValidadorCampos.validar_id("NTB-@@@")
        assert resultado is not None
        assert resultado[0] == TipoErro.ID_INVALIDO

    def test_id_vazio(self):
        """ID vazio retorna erro"""
        resultado = ValidadorCampos.validar_id("")
        assert resultado is not None
        assert resultado[0] == TipoErro.CAMPO_CRITICO_VAZIO

    def test_data_valida(self):
        """Data válida não retorna erro"""
        resultado = ValidadorCampos.validar_data("2026-04-22", "data_entrada")
        assert resultado is None

    def test_data_invalida_mes(self):
        """Data com mês 13 retorna erro"""
        resultado = ValidadorCampos.validar_data("2024-13-45", "data_entrada")
        assert resultado is not None
        assert resultado[0] == TipoErro.DATA_INVALIDA

    def test_data_futura(self):
        """Data futura retorna aviso"""
        resultado = ValidadorCampos.validar_data("2099-12-31", "data_entrada")
        assert resultado is not None
        assert resultado[0] == TipoAviso.DATA_FUTURA

    def test_email_valido(self):
        """Email válido não retorna erro"""
        resultado = ValidadorCampos.validar_email("user@example.com")
        assert resultado is None

    def test_email_invalido(self):
        """Email inválido retorna erro"""
        resultado = ValidadorCampos.validar_email("invalid@@email")
        assert resultado is not None
        assert resultado[0] == TipoErro.EMAIL_INVALIDO

    def test_email_ausente(self):
        """Email ausente retorna aviso"""
        resultado = ValidadorCampos.validar_email("")
        assert resultado is not None
        assert resultado[0] == TipoAviso.EMAIL_AUSENTE

    def test_numero_valido(self):
        """Número válido não retorna erro"""
        resultado = ValidadorCampos.validar_numero("1000.50", "valor")
        assert resultado is None

    def test_numero_negativo(self):
        """Número negativo retorna erro"""
        resultado = ValidadorCampos.validar_numero("-100", "valor")
        assert resultado is not None
        assert resultado[0] == TipoErro.NUMERO_INVALIDO

    def test_numero_invalido(self):
        """String não numérica retorna erro"""
        resultado = ValidadorCampos.validar_numero("abc", "valor")
        assert resultado is not None
        assert resultado[0] == TipoErro.NUMERO_INVALIDO

    def test_enum_valido(self):
        """Valor em enum válido não retorna erro"""
        resultado = ValidadorCampos.validar_enum(
            "Em Uso",
            "status",
            {"Em Uso", "Armazenado", "Descartado"}
        )
        assert resultado is None

    def test_enum_invalido(self):
        """Valor fora de enum retorna erro"""
        resultado = ValidadorCampos.validar_enum(
            "Desconhecido",
            "status",
            {"Em Uso", "Armazenado", "Descartado"}
        )
        assert resultado is not None
        assert resultado[0] == TipoErro.TIPO_INVALIDO

    def test_comprimento_excedido(self):
        """Campo que excede comprimento retorna erro"""
        resultado = ValidadorCampos.validar_comprimento(
            "A" * 150,
            "marca",
            100
        )
        assert resultado is not None
        assert resultado[0] == TipoErro.VALOR_EXCEDE_COMPRIMENTO


class TestValidadorLinha:
    """Testa validação de linha completa"""

    def test_linha_valida(self):
        """Linha com todos campos críticos válida passa"""
        validador = ValidadorLinha()
        linha = {
            "id": "NTB-001",
            "tipo": "Notebook",
            "marca": "Dell",
            "modelo": "Latitude",
            "departamento": "TI",
            "status": "Em Uso",
            "data_entrada": "2026-04-22"
        }
        resultado = validador.validar(linha, 1)

        assert resultado.valida
        assert len(resultado.erros) == 0
        assert resultado.id_ativo == "NTB-001"

    def test_linha_campo_critico_vazio(self):
        """Linha com campo crítico vazio falha"""
        validador = ValidadorLinha()
        linha = {
            "id": "NTB-001",
            "tipo": "",  # Vazio
            "marca": "Dell",
            "modelo": "Latitude",
            "departamento": "TI",
            "status": "Em Uso",
            "data_entrada": "2026-04-22"
        }
        resultado = validador.validar(linha, 1)

        assert not resultado.valida
        assert len(resultado.erros) > 0

    def test_linha_com_aviso(self):
        """Linha com aviso (email ausente) passa mas com aviso"""
        validador = ValidadorLinha()
        linha = {
            "id": "NTB-001",
            "tipo": "Notebook",
            "marca": "Dell",
            "modelo": "Latitude",
            "departamento": "TI",
            "status": "Em Uso",
            "data_entrada": "2026-04-22",
            "email_responsavel": ""
        }
        resultado = validador.validar(linha, 1)

        assert resultado.valida
        assert len(resultado.avisos) > 0

    def test_linha_data_invalida(self):
        """Linha com data inválida falha"""
        validador = ValidadorLinha()
        linha = {
            "id": "NTB-001",
            "tipo": "Notebook",
            "marca": "Dell",
            "modelo": "Latitude",
            "departamento": "TI",
            "status": "Em Uso",
            "data_entrada": "2024-13-45"
        }
        resultado = validador.validar(linha, 1)

        assert not resultado.valida
        assert len(resultado.erros) > 0


class TestValidadorLote:
    """Testa validação de lote completo"""

    def test_lote_valido(self):
        """Lote com 100% válidas retorna seguro"""
        validador = ValidadorLote()
        linhas = [
            {
                "id": f"NTB-{i:03d}",
                "tipo": "Notebook",
                "marca": "Dell",
                "modelo": "Latitude",
                "departamento": "TI",
                "status": "Em Uso",
                "data_entrada": "2026-04-22"
            }
            for i in range(1, 11)
        ]

        resultado = validador.validar_lote(
            linhas=linhas,
            mapeamento_campos={
                "id": ("id", 1.0),
                "tipo": ("tipo", 1.0),
                "marca": ("marca", 1.0),
                "modelo": ("modelo", 1.0),
                "departamento": ("departamento", 1.0),
                "status": ("status", 1.0),
                "data_entrada": ("data_entrada", 1.0),
            }
        )

        assert resultado.taxa_erro_percentual == 0.0
        assert len(resultado.bloqueios) == 0
        assert resultado.linhas_validas == 10

    def test_lote_com_erro_50_porcento(self):
        """Lote com >50% erro é bloqueado"""
        validador = ValidadorLote()
        linhas = [
            {
                "id": f"NTB-{i:03d}",
                "tipo": "Notebook",
                "marca": "Dell",
                "modelo": "Latitude",
                "departamento": "TI",
                "status": "Em Uso",
                "data_entrada": "2026-04-22" if i <= 4 else "2024-13-45"  # 60% erro
            }
            for i in range(1, 11)
        ]

        resultado = validador.validar_lote(
            linhas=linhas,
            mapeamento_campos={
                "id": ("id", 1.0),
                "tipo": ("tipo", 1.0),
                "marca": ("marca", 1.0),
                "modelo": ("modelo", 1.0),
                "departamento": ("departamento", 1.0),
                "status": ("status", 1.0),
                "data_entrada": ("data_entrada", 1.0),
            }
        )

        assert resultado.taxa_erro_percentual > 50
        assert len(resultado.bloqueios) > 0

    def test_lote_campo_critico_faltando(self):
        """Lote sem mapeamento de campo crítico é bloqueado"""
        validador = ValidadorLote()
        linhas = [{"id": "NTB-001", "tipo": "Notebook"}]

        resultado = validador.validar_lote(
            linhas=linhas,
            mapeamento_campos={
                "id": ("id", 1.0),
                "tipo": ("tipo", 1.0),
                # Faltam marca, modelo, departamento, status, data_entrada
            }
        )

        assert len(resultado.bloqueios) > 0


class TestClassificacaoStatus:
    """Testa classificação de status (seguro/alerta/bloqueado)"""

    def test_status_seguro(self):
        """Taxa 0% de erro, sem bloqueios = seguro"""
        status, cor = classificar_status_importacao(
            taxa_erro=0.0,
            bloqueios=[],
            avisos=[]
        )
        assert status == "seguro"
        assert cor == "green"

    def test_status_alerta(self):
        """Taxa 5% de erro, sem bloqueios = alerta"""
        status, cor = classificar_status_importacao(
            taxa_erro=5.0,
            bloqueios=[],
            avisos=["Email ausente em 5 linhas"]
        )
        assert status == "alerta"
        assert cor == "yellow"

    def test_status_bloqueado(self):
        """Com bloqueios = bloqueado"""
        status, cor = classificar_status_importacao(
            taxa_erro=0.0,
            bloqueios=["Campo crítico não mapeado: id"],
            avisos=[]
        )
        assert status == "bloqueado"
        assert cor == "red"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
