from __future__ import annotations

from datetime import date, timedelta

import pytest

import services.ativos_service as ativos_service_module
from models.ativos import Ativo
from services.ativos_service import AtivosService
from utils.validators import validar_ativo


# Monta um ativo-base válido para reaproveitar nas variações de teste.
def make_valid_ativo(**overrides):
    """
    Cria um ativo válido com os campos mínimos exigidos pela Fase 1.
    """
    base_data = {
        "id_ativo": "OPU-000001",
        "tipo": "Notebook",
        "marca": "Dell",
        "modelo": "XPS",
        "serial": "SN-001",
        "usuario_responsavel": None,
        "departamento": "T.I",
        "status": "Disponível",
        "data_entrada": date.today().isoformat(),
        "data_saida": None,
        "criado_por": 1,
        "codigo_interno": "PAT-001",
        "descricao": "Notebook corporativo",
        "categoria": "Computadores",
        "tipo_ativo": "Notebook",
        "condicao": "Novo",
        "localizacao": "Matriz",
        "setor": "T.I",
        "email_responsavel": None,
        "data_compra": date.today().isoformat(),
        "valor": "4500.00",
        "observacoes": None,
    }
    base_data.update(overrides)
    return Ativo(**base_data)


class FakeCursor:
    """
    Cursor simples para simular o INSERT sem depender de banco real.
    """

    def __init__(self):
        self.statements = []
        self.rowcount = 0
        self.fetchone_queue = []

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        sql_upper = (sql or "").lstrip().upper()
        self.rowcount = 1 if sql_upper.startswith(("INSERT", "UPDATE", "DELETE")) else 0

    def fetchone(self):
        if self.fetchone_queue:
            return self.fetchone_queue.pop(0)
        return None

    def fetchall(self):
        return []


class FakeCursorContext:
    """
    Context manager mínimo compatível com cursor_mysql.
    """

    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return None, self.cursor

    def __exit__(self, exc_type, exc, tb):
        return False


def _atualizar_fechas_ativo(ativo: Ativo, **overrides) -> Ativo:
    """
    Gera uma cópia do ativo para simular o estado anterior ou o estado novo da edição.
    """
    dados = ativo.to_dict()
    # O construtor do domínio recebe os nomes novos; os aliases legados são descartados aqui.
    dados.pop("criado_em", None)
    dados.pop("atualizado_em", None)
    dados.update(overrides)
    return Ativo(**dados)


def _row_db_from_ativo(ativo: Ativo, **overrides) -> dict:
    """
    Monta uma linha de banco mínima para testar o mapeamento do service.
    """
    row = {
        "id": ativo.id_ativo or "OPU-000001",
        "codigo_interno": ativo.codigo_interno,
        "tipo": ativo.tipo,
        "marca": ativo.marca,
        "modelo": ativo.modelo,
        "serial": ativo.serial,
        "descricao": ativo.descricao,
        "categoria": ativo.categoria,
        "tipo_ativo": ativo.tipo_ativo,
        "condicao": ativo.condicao,
        "localizacao": ativo.localizacao,
        "setor": ativo.setor,
        "usuario_responsavel": ativo.usuario_responsavel,
        "email_responsavel": ativo.email_responsavel,
        "departamento": ativo.departamento,
        "nota_fiscal": ativo.nota_fiscal,
        "garantia": ativo.garantia,
        "status": ativo.status,
        "data_entrada": ativo.data_entrada,
        "data_saida": ativo.data_saida,
        "data_compra": ativo.data_compra,
        "valor": ativo.valor,
        "observacoes": ativo.observacoes,
        "detalhes_tecnicos": ativo.detalhes_tecnicos,
        "processador": ativo.processador,
        "ram": ativo.ram,
        "armazenamento": ativo.armazenamento,
        "sistema_operacional": ativo.sistema_operacional,
        "carregador": ativo.carregador,
        "teamviewer_id": ativo.teamviewer_id,
        "anydesk_id": ativo.anydesk_id,
        "nome_equipamento": ativo.nome_equipamento,
        "hostname": ativo.hostname,
        "imei_1": ativo.imei_1,
        "imei_2": ativo.imei_2,
        "numero_linha": ativo.numero_linha,
        "operadora": ativo.operadora,
        "conta_vinculada": ativo.conta_vinculada,
        "polegadas": ativo.polegadas,
        "resolucao": ativo.resolucao,
        "tipo_painel": ativo.tipo_painel,
        "entrada_video": ativo.entrada_video,
        "fonte_ou_cabo": ativo.fonte_ou_cabo,
        "created_at": ativo.created_at,
        "updated_at": ativo.updated_at,
        "data_ultima_movimentacao": ativo.data_ultima_movimentacao,
        "criado_por": ativo.criado_por,
    }
    row.update(overrides)
    return row


def test_validar_ativo_rejeita_tipo_invalido():
    """
    O backend deve bloquear tipo_ativo fora da lista oficial.
    """
    ativo = make_valid_ativo(tipo_ativo="Tablet")

    try:
        validar_ativo(ativo, validar_id=False)
    except ValueError as erro:
        assert "Tipo de ativo inválido" in str(erro)
    else:
        raise AssertionError("Era esperado ValueError para tipo_ativo inválido.")


def test_validar_ativo_rejeita_em_uso_sem_responsavel():
    """
    O status Em Uso exige responsável preenchido.
    """
    ativo = make_valid_ativo(status="Em Uso", usuario_responsavel=None)

    try:
        validar_ativo(ativo, validar_id=False)
    except ValueError as erro:
        assert "Em Uso" in str(erro)
        assert "responsável" in str(erro).lower()
    else:
        raise AssertionError("Era esperado ValueError para Em Uso sem responsável.")


def test_validar_ativo_rejeita_data_entrada_futura():
    """
    A data de entrada não pode ficar no futuro.
    """
    ativo = make_valid_ativo(data_entrada=(date.today() + timedelta(days=1)).isoformat())

    try:
        validar_ativo(ativo, validar_id=False)
    except ValueError as erro:
        assert "data_entrada" in str(erro)
        assert "futura" in str(erro).lower()
    else:
        raise AssertionError("Era esperado ValueError para data_entrada futura.")


def test_validar_ativo_rejeita_data_compra_maior_que_data_entrada():
    """
    A data de compra não pode ser posterior à data de entrada.
    """
    hoje = date.today().isoformat()
    ativo = make_valid_ativo(
        data_entrada=hoje,
        data_compra=(date.today() + timedelta(days=1)).isoformat(),
    )

    try:
        validar_ativo(ativo, validar_id=False)
    except ValueError as erro:
        assert "data da compra" in str(erro).lower()
    else:
        raise AssertionError("Era esperado ValueError para data_compra maior que data_entrada.")


def test_criar_ativo_aceita_payload_legado_com_tipo_e_departamento(monkeypatch):
    """
    O service mantém compatibilidade com payload legado usando tipo e departamento.
    """
    service = AtivosService()
    cursor = FakeCursor()

    # Simula contexto de usuário sem tocar no banco real.
    monkeypatch.setattr(
        service,
        "_obter_contexto_acesso",
        lambda _user_id: {"empresa_id": 1, "perfil": "usuario"},
    )
    monkeypatch.setattr(service, "_gerar_id_sequencial", lambda _empresa_id, _conn, _cur: "OPU-000001")
    monkeypatch.setattr(ativos_service_module, "cursor_mysql", lambda dictionary=True: FakeCursorContext(cursor))

    ativo_legado = Ativo(
        id_ativo=None,
        tipo="Notebook",
        marca="Dell",
        modelo="XPS",
        serial="SN-LEGADO",
        usuario_responsavel=None,
        departamento="T.I",
        status="Disponível",
        data_entrada=date.today().isoformat(),
        data_saida=None,
        criado_por=None,
        codigo_interno=None,
        descricao=None,
        categoria=None,
        tipo_ativo=None,
        condicao=None,
        localizacao=None,
        setor=None,
        email_responsavel=None,
        data_compra=None,
        valor=None,
        observacoes=None,
    )

    id_gerado = service.criar_ativo(ativo_legado, user_id=1)

    assert id_gerado == "OPU-000001"
    assert any("INSERT INTO ativos" in sql for sql, _params in cursor.statements)


@pytest.mark.parametrize(
    "cenario, esperado_tipo, esperado_status",
    [
        ("entrega", "entrega_para_colaborador", "Em Uso"),
        ("devolucao", "devolucao_ao_estoque", "Disponível"),
        ("troca", "troca_de_responsavel", "Em Uso"),
        ("transferencia", "transferencia_interna", "Disponível"),
        ("manutencao", "envio_para_manutencao", "Em Manutenção"),
    ],
)
def test_analisar_movimentacao_ativo_classifica_casos_principais(cenario, esperado_tipo, esperado_status):
    """
    O resumo central deve identificar a movimentação e a sugestão de status.
    """
    service = AtivosService()

    atual = make_valid_ativo(status="Disponível", usuario_responsavel=None, setor="T.I", localizacao="Matriz")
    if cenario in {"devolucao", "troca"}:
        atual = make_valid_ativo(status="Em Uso", usuario_responsavel="Ana Silva", setor="T.I", localizacao="Matriz")

    if cenario == "entrega":
        novo = _atualizar_fechas_ativo(atual, usuario_responsavel="Ana Silva", status="Disponível")
    elif cenario == "devolucao":
        novo = _atualizar_fechas_ativo(atual, usuario_responsavel=None, status="Em Uso")
    elif cenario == "troca":
        novo = _atualizar_fechas_ativo(atual, usuario_responsavel="Beatriz Costa", status="Disponível")
    elif cenario == "transferencia":
        novo = _atualizar_fechas_ativo(atual, setor="Logística", departamento="Logística", localizacao="Filial 2")
    else:
        novo = _atualizar_fechas_ativo(atual, status="Em Manutenção")

    resumo = service.analisar_movimentacao_ativo(atual, novo)

    assert resumo["tipo_movimentacao"] == esperado_tipo
    assert resumo["status_sugerido"] == esperado_status
    assert isinstance(resumo["campos_alterados"], list)
    assert "estado_anterior" in resumo and "estado_novo" in resumo


def test_analisar_movimentacao_ativo_retorna_resumo_com_antes_depois():
    """
    O contrato do resumo precisa carregar o comparativo para o modal da próxima fase.
    """
    service = AtivosService()
    atual = make_valid_ativo(status="Disponível", usuario_responsavel=None, setor="T.I", localizacao="Matriz")
    novo = _atualizar_fechas_ativo(atual, usuario_responsavel="Ana Silva", status="Disponível")

    resumo = service.analisar_movimentacao_ativo(atual, novo)

    assert resumo["mudanca_relevante"] is True
    assert resumo["atualizar_data_ultima_movimentacao"] is True
    assert resumo["tipo_movimentacao"] == "entrega_para_colaborador"
    assert any(item["campo"] == "usuario_responsavel" for item in resumo["campos_alterados"])
    assert all("antes" in item and "depois" in item for item in resumo["campos_alterados"])


def test_analisar_movimentacao_ativo_lista_apenas_campos_realmente_alterados():
    """
    O resumo de movimentação não deve incluir campos que permaneceram iguais.
    """
    service = AtivosService()
    atual = make_valid_ativo(status="Disponível", usuario_responsavel=None, setor="T.I", localizacao="Matriz")
    novo = _atualizar_fechas_ativo(atual, localizacao="Filial 2")

    resumo = service.analisar_movimentacao_ativo(atual, novo)
    campos = [item["campo"] for item in resumo["campos_alterados"]]

    assert "localizacao" in campos
    assert "status" not in campos
    assert "usuario_responsavel" not in campos
    assert "setor" not in campos


def test_atualizar_ativo_simple_nao_altera_movimentacao(monkeypatch):
    """
    Alteração técnica isolada não deve atualizar a data de movimentação.
    """
    service = AtivosService()
    cursor = FakeCursor()

    atual = make_valid_ativo(status="Disponível", usuario_responsavel=None, setor="T.I", localizacao="Matriz")
    atualizado = _atualizar_fechas_ativo(atual, processador="Intel Core i7")
    cursor.fetchone_queue = [
        _row_db_from_ativo(atual, created_at="2026-04-01 10:00:00", updated_at="2026-04-01 10:00:00", data_ultima_movimentacao=None),
        _row_db_from_ativo(atualizado, created_at="2026-04-01 10:00:00", updated_at="2026-04-14 11:00:00", data_ultima_movimentacao=None),
    ]

    monkeypatch.setattr(
        service,
        "_obter_contexto_acesso",
        lambda _user_id: {"empresa_id": 1, "perfil": "usuario"},
    )
    monkeypatch.setattr(ativos_service_module, "cursor_mysql", lambda dictionary=True: FakeCursorContext(cursor))

    resultado = service.atualizar_ativo(atual.id_ativo, {"processador": "Intel Core i7"}, user_id=1)

    assert resultado.resumo_movimentacao["tipo_movimentacao"] == "atualizacao_cadastral"
    assert resultado.resumo_movimentacao["atualizar_data_ultima_movimentacao"] is False
    update_sql = next(sql for sql, _params in cursor.statements if sql.strip().upper().startswith("UPDATE"))
    assert "data_ultima_movimentacao" not in update_sql


def test_atualizar_ativo_preenche_responsavel_sugere_em_uso(monkeypatch):
    """
    Ao preencher responsável em um ativo disponível, o backend sugere Em Uso.
    """
    service = AtivosService()
    cursor = FakeCursor()

    atual = make_valid_ativo(status="Disponível", usuario_responsavel=None, setor="T.I", localizacao="Matriz")
    cursor.fetchone_queue = [
        _row_db_from_ativo(atual, created_at="2026-04-01 10:00:00", updated_at="2026-04-01 10:00:00", data_ultima_movimentacao=None),
        _row_db_from_ativo(
            _atualizar_fechas_ativo(atual, usuario_responsavel="Ana Silva", status="Disponível"),
            created_at="2026-04-01 10:00:00",
            updated_at="2026-04-14 11:00:00",
            data_ultima_movimentacao="2026-04-14 11:00:00",
        ),
    ]

    monkeypatch.setattr(
        service,
        "_obter_contexto_acesso",
        lambda _user_id: {"empresa_id": 1, "perfil": "usuario"},
    )
    monkeypatch.setattr(ativos_service_module, "cursor_mysql", lambda dictionary=True: FakeCursorContext(cursor))

    resultado = service.atualizar_ativo(atual.id_ativo, {"usuario_responsavel": "Ana Silva", "status": "Disponível"}, user_id=1)

    assert resultado.resumo_movimentacao["tipo_movimentacao"] == "entrega_para_colaborador"
    assert resultado.resumo_movimentacao["status_sugerido"] == "Em Uso"
    assert resultado.data_ultima_movimentacao == "2026-04-14 11:00:00"


def test_preparar_dados_confirmacao_movimentacao_nao_exige_campos_cadastrais():
    """
    A etapa de confirmação deve aceitar payload operacional sem descrição/categoria/condição.
    """
    service = AtivosService()

    dados_formulario = {
        "status": "Disponível",
        "setor": "TI",
        "localizacao": "Matriz",
        "usuario_responsavel": None,
    }
    ajustes = {
        "status_final": "Em Uso",
        "usuario_responsavel": "Ana Silva",
        "setor": "Logística",
        "localizacao": "CD-01",
        "observacao_movimentacao": "Entrega confirmada no balcão",
    }

    dados_finais = service.preparar_dados_confirmacao_movimentacao(dados_formulario, ajustes)

    assert dados_finais["status"] == "Em Uso"
    assert dados_finais["usuario_responsavel"] == "Ana Silva"
    assert dados_finais["setor"] == "Logística"
    assert dados_finais["departamento"] == "Logística"
    assert dados_finais["localizacao"] == "CD-01"
    assert "[Movimentação]" in dados_finais["observacoes"]
    assert "descricao" not in dados_finais
    assert "categoria" not in dados_finais
    assert "condicao" not in dados_finais


def test_criar_ativo_legado_mantem_compatibilidade_com_tipo_e_departamento(monkeypatch):
    """
    O fluxo de criação continua aceitando os nomes legados sem quebrar a base nova.
    """
    service = AtivosService()
    cursor = FakeCursor()

    monkeypatch.setattr(
        service,
        "_obter_contexto_acesso",
        lambda _user_id: {"empresa_id": 1, "perfil": "usuario"},
    )
    monkeypatch.setattr(service, "_gerar_id_sequencial", lambda _empresa_id, _conn, _cur: "OPU-000001")
    monkeypatch.setattr(ativos_service_module, "cursor_mysql", lambda dictionary=True: FakeCursorContext(cursor))

    ativo_legado = Ativo(
        id_ativo=None,
        tipo="Notebook",
        marca="Dell",
        modelo="XPS",
        serial="SN-LEGADO",
        usuario_responsavel=None,
        departamento="T.I",
        status="Disponível",
        data_entrada=date.today().isoformat(),
        data_saida=None,
        criado_por=None,
        codigo_interno=None,
        descricao=None,
        categoria=None,
        tipo_ativo=None,
        condicao=None,
        localizacao=None,
        setor=None,
        email_responsavel=None,
        data_compra=None,
        valor=None,
        observacoes=None,
    )

    id_gerado = service.criar_ativo(ativo_legado, user_id=1)

    assert id_gerado == "OPU-000001"
    assert any("INSERT INTO ativos" in sql for sql, _params in cursor.statements)
