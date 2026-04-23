"""
Testes de robustez para leitura de CSV na importacao em massa.

Objetivo: Garantir que CSV malformado gera erro 400 controlado (AtivoErro),
nao erro 500 (AttributeError).

Cenarios testados:
1. CSV com linha com mais colunas que cabeçalho
2. CSV com célula contendo vírgula sem aspas adequadas
3. CSV válido (caso positivo)
4. Preview retorna erro 400, nao 500
"""

import pytest
from services.ativos_service import AtivosService, AtivoErro


def _service_admin() -> AtivosService:
    """Cria service com contexto administrativo para liberar importação em testes."""
    service = AtivosService()
    service._obter_contexto_acesso = lambda _user_id: {
        "perfil": "adm",
        "empresa_id": 1,
    }
    return service


# ============================================================================
# TESTE 1: CSV COM LINHA COM MAIS COLUNAS QUE CABECALHO
# ============================================================================

def test_csv_malformado_colunas_excedentes_levanta_ativo_erro():
    """
    CSV com linha contendo mais colunas que o cabeçalho deve levantar AtivoErro.

    Exemplo: cabeçalho tem 3 colunas, linha tem 5 valores.
    DictReader coloca os valores excedentes na chave None.
    """
    service = _service_admin()

    # CSV malformado: cabeçalho tem 3 colunas, linha 2 tem 5
    csv_malformado = (
        "tipo_ativo,marca,modelo\n"
        "Notebook,Dell,XPS,EXTRA_COLUNA_1,EXTRA_COLUNA_2\n"
    ).encode("utf-8")

    with pytest.raises(AtivoErro) as exc_info:
        service.gerar_preview_importacao_csv(csv_malformado, user_id=1)

    erro_msg = str(exc_info.value)
    # Deve mencionar linha 2 (primeira linha de dados)
    assert "Linha 2" in erro_msg
    # Deve mencionar colunas excedentes
    assert "colunas" in erro_msg.lower()
    # Deve não ser AttributeError
    assert isinstance(exc_info.value, AtivoErro)


# ============================================================================
# TESTE 2: CSV COM CÉLULA CONTENDO VIRGULA SEM ASPAS ADEQUADAS
# ============================================================================

def test_csv_malformado_virgula_em_celula_sem_aspas():
    """
    Célula com vírgula sem aspas causa desalinhamento de colunas.

    Exemplo: "Notebook,Dell,XPS 15, com mouse" (vírgula no modelo)
    Sem aspas: Notebook | Dell | XPS 15 | com mouse (4 colunas em vez de 3)
    """
    service = _service_admin()

    # CSV com célula contendo vírgula, sem aspas
    csv_malformado = (
        "tipo_ativo,marca,modelo\n"
        "Notebook,Dell,XPS 15, com mouse\n"
    ).encode("utf-8")

    with pytest.raises(AtivoErro) as exc_info:
        service.gerar_preview_importacao_csv(csv_malformado, user_id=1)

    erro_msg = str(exc_info.value)
    assert "Linha 2" in erro_msg
    assert "colunas" in erro_msg.lower()


# ============================================================================
# TESTE 3: CSV VÁLIDO COM DADOS NORMAIS (CASO POSITIVO)
# ============================================================================

def test_csv_valido_carrega_corretamente():
    """
    CSV bem-formado com dados válidos deve carregar sem erro.
    """
    service = _service_admin()

    # CSV válido
    csv_valido = (
        "tipo_ativo,marca,modelo,setor,status,data_entrada\n"
        "Notebook,Dell,XPS,T.I,Disponível,2026-04-17\n"
        "Desktop,HP,ProDesk,Financeiro,Disponível,2026-04-16\n"
    ).encode("utf-8")

    # Não deve levantar erro
    resultado = service.gerar_preview_importacao_csv(csv_valido, user_id=1)

    # Deve retornar estrutura válida
    assert "colunas" in resultado
    assert "preview_linhas" in resultado
    assert "resumo_validacao" in resultado
    assert resultado["resumo_validacao"]["total_linhas"] == 2


# ============================================================================
# TESTE 4: CSV COM ASPAS CORRETAS (ESCAPE DE VIRGULA)
# ============================================================================

def test_csv_com_aspas_escapa_virgula_corretamente():
    """
    Quando célula tem aspas, vírgula dentro é escapada corretamente.
    """
    service = _service_admin()

    # CSV com aspas escapando vírgula
    csv_valido = (
        'tipo_ativo,marca,modelo\n'
        'Notebook,Dell,"XPS 15, com mouse"\n'
    ).encode("utf-8")

    # Deve carregar sem erro (o DictReader entende as aspas)
    resultado = service.gerar_preview_importacao_csv(csv_valido, user_id=1)

    assert resultado["resumo_validacao"]["total_linhas"] == 1
    assert resultado["resumo_validacao"]["linhas_validas"] >= 0  # Pode não ser válido por domínio, mas não deve quebrar


# ============================================================================
# TESTE 5: CSV VAZIO
# ============================================================================

def test_csv_vazio_levanta_ativo_erro():
    """CSV vazio deve levantar AtivoErro controlado."""
    service = _service_admin()

    csv_vazio = b""

    with pytest.raises(AtivoErro) as exc_info:
        service.gerar_preview_importacao_csv(csv_vazio, user_id=1)

    assert "vazio" in str(exc_info.value).lower()


# ============================================================================
# TESTE 6: CSV COM CABECALHO APENAS (SEM DADOS)
# ============================================================================

def test_csv_cabecalho_sem_dados_levanta_ativo_erro():
    """CSV com apenas cabeçalho (sem linhas de dados) deve levantar AtivoErro."""
    service = _service_admin()

    csv_apenas_cabecalho = "tipo_ativo,marca,modelo\n".encode("utf-8")

    with pytest.raises(AtivoErro) as exc_info:
        service.gerar_preview_importacao_csv(csv_apenas_cabecalho, user_id=1)

    assert "linhas de dados" in str(exc_info.value).lower()


# ============================================================================
# TESTE 7: CSV COM ENCODING ERRADO
# ============================================================================

def test_csv_encoding_invalido_levanta_ativo_erro():
    """CSV com encoding inválido deve levantar AtivoErro controlado."""
    service = _service_admin()

    # Simular bytes não UTF-8 (por exemplo, Latin-1 com caracteres especiais)
    csv_encoding_errado = "tipo_ativo,marca,modelo\nNotebook,Marcá Especial,XPS\n".encode("latin-1")

    with pytest.raises(AtivoErro) as exc_info:
        service.gerar_preview_importacao_csv(csv_encoding_errado, user_id=1)

    # Pode ser UTF-8 ou encoding error
    assert isinstance(exc_info.value, AtivoErro)


# ============================================================================
# TESTE 8: VALORES COM ESPACOS SAO LIMPOS
# ============================================================================

def test_csv_valores_com_espacos_sao_normalizados():
    """
    Valores com espaços em branco antes/depois devem ser limpos.
    """
    service = _service_admin()

    csv_com_espacos = (
        "tipo_ativo,marca,modelo\n"
        "  Notebook  ,  Dell  ,  XPS  \n"  # Espaços antes/depois
    ).encode("utf-8")

    resultado = service.gerar_preview_importacao_csv(csv_com_espacos, user_id=1)

    # Verificar que preview contém dados (sem espaços extras)
    preview = resultado["preview_linhas"][0]["dados_mapeados"]
    # Os valores devem estar limpos
    assert preview.get("tipo_ativo") == "Notebook"  # Sem espaços
    assert preview.get("marca") == "Dell"  # Sem espaços


# ============================================================================
# TESTE 9: LINHAS VAZIAS SAO IGNORADAS
# ============================================================================

def test_csv_linhas_vazias_sao_ignoradas():
    """
    Linhas completamente vazias devem ser ignoradas (sem ruído).
    """
    service = _service_admin()

    csv_com_linhas_vazias = (
        "tipo_ativo,marca,modelo\n"
        "Notebook,Dell,XPS\n"
        "\n"  # Linha vazia
        "Desktop,HP,ProDesk\n"
        ",,\n"  # Linha com apenas separadores (vazia)
    ).encode("utf-8")

    resultado = service.gerar_preview_importacao_csv(csv_com_linhas_vazias, user_id=1)

    # Deve ter apenas 2 linhas válidas (a 1ª e 3ª)
    assert resultado["resumo_validacao"]["total_linhas"] == 2
    assert len(resultado["preview_linhas"]) == 2
