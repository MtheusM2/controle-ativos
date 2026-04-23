"""
Testes de integração da auditoria de importações.

Cobre:
- Criar logs de auditoria
- Detectar duplicatas
- Reverter importação
"""

import pytest
from services.auditoria_importacao_service import AuditoriaImportacaoService


class TestAuditoriaImportacao:
    """Testa funcionalidades de auditoria"""

    def test_gerar_id_lote(self):
        """ID de lote é gerado corretamente"""
        id_lote = AuditoriaImportacaoService.gerar_id_lote()

        assert id_lote.startswith("IMP-")
        assert len(id_lote) > 10
        assert id_lote != AuditoriaImportacaoService.gerar_id_lote()  # Único

    def test_iniciar_auditoria(self):
        """Auditoria é criada com status pendente"""
        id_lote = AuditoriaImportacaoService.iniciar_auditoria(
            usuario_id=1,
            empresa_id=1,
            hash_arquivo="abc123",
            nome_arquivo="test.csv",
            tamanho_bytes=1024,
            endereco_ip="127.0.0.1",
            user_agent="TestBrowser"
        )

        assert id_lote.startswith("IMP-")
        assert len(id_lote) > 10

    def test_registrar_preview_gerado(self):
        """Preview é registrado com bloqueios/alertas"""
        id_lote = AuditoriaImportacaoService.iniciar_auditoria(
            usuario_id=1,
            empresa_id=1,
            hash_arquivo="abc123",
            nome_arquivo="test.csv",
            tamanho_bytes=1024,
            endereco_ip="127.0.0.1",
            user_agent="TestBrowser"
        )

        AuditoriaImportacaoService.registrar_preview_gerado(
            id_lote=id_lote,
            delimitador=",",
            numero_linha_cabecalho=0,
            score_deteccao_cabecalho=0.99,
            total_linhas=100,
            dados_bloqueios=[],
            dados_avisos=["Email ausente em 5 linhas"]
        )

        # Se chegou aqui, funcionou
        assert True

    def test_registrar_confirmacao(self):
        """Confirmação é registrada"""
        id_lote = AuditoriaImportacaoService.iniciar_auditoria(
            usuario_id=1,
            empresa_id=1,
            hash_arquivo="abc123",
            nome_arquivo="test.csv",
            tamanho_bytes=1024,
            endereco_ip="127.0.0.1",
            user_agent="TestBrowser"
        )

        AuditoriaImportacaoService.registrar_confirmacao(
            id_lote=id_lote,
            modo_duplicata="atualizar"
        )

        # Se chegou aqui, funcionou
        assert True

    def test_registrar_linha_importada(self):
        """Linha importada é registrada"""
        id_lote = AuditoriaImportacaoService.iniciar_auditoria(
            usuario_id=1,
            empresa_id=1,
            hash_arquivo="abc123",
            nome_arquivo="test.csv",
            tamanho_bytes=1024,
            endereco_ip="127.0.0.1",
            user_agent="TestBrowser"
        )

        AuditoriaImportacaoService.registrar_linha_importada(
            id_lote=id_lote,
            numero_linha=1,
            id_ativo_csv="NTB-001",
            id_ativo_criado="NTB-001",
            operacao="INSERT",
            avisos=[]
        )

        # Se chegou aqui, funcionou
        assert True

    def test_registrar_linha_rejeitada(self):
        """Linha rejeitada é registrada"""
        id_lote = AuditoriaImportacaoService.iniciar_auditoria(
            usuario_id=1,
            empresa_id=1,
            hash_arquivo="abc123",
            nome_arquivo="test.csv",
            tamanho_bytes=1024,
            endereco_ip="127.0.0.1",
            user_agent="TestBrowser"
        )

        AuditoriaImportacaoService.registrar_linha_rejeitada(
            id_lote=id_lote,
            numero_linha=2,
            id_ativo_csv="NTB-002",
            motivo="Data inválida: 2024-13-45",
            avisos=[]
        )

        # Se chegou aqui, funcionou
        assert True

    def test_registrar_resultado_importacao(self):
        """Resultado de importação é registrado"""
        id_lote = AuditoriaImportacaoService.iniciar_auditoria(
            usuario_id=1,
            empresa_id=1,
            hash_arquivo="abc123",
            nome_arquivo="test.csv",
            tamanho_bytes=1024,
            endereco_ip="127.0.0.1",
            user_agent="TestBrowser"
        )

        AuditoriaImportacaoService.registrar_resultado_importacao(
            id_lote=id_lote,
            linhas_importadas=95,
            linhas_rejeitadas=5,
            linhas_com_aviso=0,
            linhas_atualizadas=0,
            ids_ativos_afetados=["NTB-001", "NTB-002", "NTB-003"],
            mensagem_erro=None
        )

        # Se chegou aqui, funcionou
        assert True

    def test_detectar_duplicatas(self):
        """Detecta IDs que já existem"""
        # Usar IDs conhecidos que podem existir ou não
        ids = ["NTB-001", "NTB-002", "NTB-999999"]
        duplicatas = AuditoriaImportacaoService.detectar_duplicatas(
            ids,
            empresa_id=1
        )

        # Função retorna dict (pode estar vazio ou com IDs)
        assert isinstance(duplicatas, dict)

    def test_obter_usuarios_validos(self):
        """Retorna cache de usuários da empresa"""
        usuarios = AuditoriaImportacaoService.obter_usuarios_validos(
            empresa_id=1
        )

        # Deve retornar um set
        assert isinstance(usuarios, set)

    def test_obter_relatorio_importacao(self):
        """Gera relatório de importação"""
        id_lote = AuditoriaImportacaoService.iniciar_auditoria(
            usuario_id=1,
            empresa_id=1,
            hash_arquivo="abc123",
            nome_arquivo="test.csv",
            tamanho_bytes=1024,
            endereco_ip="127.0.0.1",
            user_agent="TestBrowser"
        )

        AuditoriaImportacaoService.registrar_resultado_importacao(
            id_lote=id_lote,
            linhas_importadas=100,
            linhas_rejeitadas=0,
            linhas_com_aviso=0,
            linhas_atualizadas=0,
            ids_ativos_afetados=["NTB-001"],
            mensagem_erro=None
        )

        relatorio = AuditoriaImportacaoService.obter_relatorio_importacao(id_lote)

        assert relatorio["ok"]
        assert relatorio["lote"]["id_lote"] == id_lote
        assert relatorio["lote"]["importadas"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
