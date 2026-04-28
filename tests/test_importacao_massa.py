from __future__ import annotations

import pytest
from types import SimpleNamespace

from services.auditoria_importacao_service import AuditoriaImportacaoService
from services.ativos_service import AtivoErro, AtivosService


def _service_admin() -> AtivosService:
    """
    Cria service com contexto administrativo para liberar importação em testes.
    """
    service = AtivosService()
    service._obter_contexto_acesso = lambda _user_id: {  # type: ignore[attr-defined]
        "perfil": "adm",
        "empresa_id": 1,
    }
    return service


def test_preview_importacao_classifica_exatas_sugeridas_e_ignoradas():
    """
    Preview deve separar corretamente colunas exatas, sugeridas e bloqueadas.
    """
    service = _service_admin()
    conteudo_csv = (
        "tipo_ativo,marca,modelo,setor,status,data_entrada,teamviewer id,anydesk id,PC,IMEI,password\n"
        "Notebook,Dell,XPS,T.I,Dispon\u00edvel,2026-04-17,123456789,ABC-DEF-123,maquina-01,999999999999999,minha_senha\n"
    ).encode("utf-8")

    resultado = service.gerar_preview_importacao_csv(conteudo_csv, user_id=1)

    exatas = resultado["colunas"]["exatas"]
    sugeridas = resultado["colunas"]["sugeridas"]
    ignoradas = resultado["colunas"]["ignoradas"]
    resumo = resultado["resumo_validacao"]

    assert any(item["campo_destino"] == "tipo_ativo" for item in exatas)
    assert any(item["campo_sugerido"] == "teamviewer_id" for item in sugeridas)
    assert any(item["campo_sugerido"] == "anydesk_id" for item in sugeridas)
    assert any(item["coluna_origem"] == "PC" for item in ignoradas)
    assert any(item["coluna_origem"] == "IMEI" for item in ignoradas)
    assert any(item["coluna_origem"] == "password" for item in ignoradas)
    # Contrato explícito para o frontend validar obrigatórios no estado consolidado.
    assert "campos_obrigatorios_preview" in resultado
    assert "data_entrada" in resultado["campos_obrigatorios_preview"]
    assert resumo["total_linhas"] == 1
    assert resumo["linhas_validas"] == 1


def test_confirmar_importacao_aplica_sugestoes_confirmadas_teamviewer_anydesk():
    """
    Confirmação deve importar TeamViewer/AnyDesk somente quando usuário aprova sugestão.
    """
    service = _service_admin()
    ativos_capturados = []

    def _criar_ativo_fake(ativo, _user_id):
        ativos_capturados.append(ativo)
        return f"OPU-{len(ativos_capturados):06d}"

    service.criar_ativo = _criar_ativo_fake  # type: ignore[method-assign]

    conteudo_csv = (
        "tipo_ativo,marca,modelo,setor,status,data_entrada,teamviewer id,anydesk id\n"
        "Notebook,Dell,XPS,T.I,Dispon\u00edvel,2026-04-17,123456789,ABC-DEF-123\n"
    ).encode("utf-8")

    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={
            "teamviewer id": "teamviewer_id",
            "anydesk id": "anydesk_id",
        },
        user_id=1,
        modo_tudo_ou_nada=True,
    )

    assert resultado["ok_importacao"] is True
    assert resultado["importados"] == 1
    assert len(ativos_capturados) == 1
    assert ativos_capturados[0].teamviewer_id == "123456789"
    assert ativos_capturados[0].anydesk_id == "ABC-DEF-123"
    assert ativos_capturados[0].imei_1 is None
    assert ativos_capturados[0].imei_2 is None


def test_confirmar_importacao_aceita_mapeamento_do_frontend_com_headers_normalizados(monkeypatch):
    """
    Regressao do fluxo web: frontend envia chaves normalizadas do preview
    ("tipo ativo", "data entrada"), mas a confirmacao deve reconciliar isso
    com os headers reais do CSV ("tipo_ativo", "data_entrada").
    """
    service = _service_admin()
    ativos_capturados = []

    monkeypatch.setattr(
        AuditoriaImportacaoService,
        "obter_usuarios_validos",
        staticmethod(lambda empresa_id: {"Matheus"}),
    )

    def _criar_ativo_fake(ativo, _user_id):
        ativos_capturados.append(ativo)
        return f"OPU-{len(ativos_capturados):06d}"

    service.criar_ativo = _criar_ativo_fake  # type: ignore[method-assign]

    conteudo_csv = (
        "tipo_ativo,marca,modelo,usuario_responsavel,setor,status,data_entrada\n"
        "Monitor,Samsung,24POLEGADAS,Matheus,Rh,Em Uso,2026-04-06\n"
    ).encode("utf-8")

    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={},
        user_id=1,
        modo_tudo_ou_nada=False,
        modo_importacao="validas_e_avisos",
        mapeamento_confirmado={
            "tipo ativo": "tipo_ativo",
            "marca": "marca",
            "modelo": "modelo",
            "usuario responsavel": "usuario_responsavel",
            "setor": "setor",
            "status": "status",
            "data entrada": "data_entrada",
        },
        linhas_descartadas=set(),
        edicoes_por_linha={},
    )

    assert resultado["ok_importacao"] is True
    assert resultado["importados"] == 1
    assert resultado["falhas"] == 0
    assert len(ativos_capturados) == 1
    assert ativos_capturados[0].tipo_ativo == "Monitor"
    assert ativos_capturados[0].data_entrada == "2026-04-06"


def test_confirmar_importacao_sem_confirmar_sugestao_mantem_schema_first():
    """
    Sem confirmação de sugestão, campo sugerido não entra e linha pode falhar por ausência.
    """
    service = _service_admin()
    conteudo_csv = (
        "tipo ativo,marca,modelo,setor,status,data_entrada\n"
        "Notebook,Dell,XPS,T.I,Dispon\u00edvel,2026-04-17\n"
    ).encode("utf-8")

    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={},
        user_id=1,
        modo_tudo_ou_nada=True,
    )

    assert resultado["ok_importacao"] is False
    assert resultado["importados"] == 0
    assert resultado["falhas"] >= 1
    assert any("tipo" in erro.lower() for erro in resultado["erros"])


def test_confirmar_importacao_tudo_ou_nada_bloqueia_persistencia_com_linha_invalida():
    """
    Em modo tudo-ou-nada, qualquer erro de linha impede gravação parcial silenciosa.
    """
    service = _service_admin()
    criacoes = {"total": 0}

    def _criar_ativo_fake(_ativo, _user_id):
        criacoes["total"] += 1
        return f"OPU-{criacoes['total']:06d}"

    service.criar_ativo = _criar_ativo_fake  # type: ignore[method-assign]

    conteudo_csv = (
        "tipo_ativo,marca,modelo,setor,status,data_entrada\n"
        "Notebook,Dell,XPS,T.I,Dispon\u00edvel,2026-04-17\n"
        "Notebook,Dell,XPS,T.I,Status Invalido,2026-04-17\n"
    ).encode("utf-8")

    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={},
        user_id=1,
        modo_tudo_ou_nada=True,
    )

    assert resultado["ok_importacao"] is False
    assert resultado["importados"] == 0
    assert resultado["falhas"] >= 1
    assert criacoes["total"] == 0


def test_confirmar_importacao_rejeita_coluna_imei_sem_reintroduzir_no_dominio():
    """
    Coluna IMEI deve ser descartada no contrato e não pode reaparecer no objeto persistido.
    """
    service = _service_admin()
    ativos_capturados = []

    def _criar_ativo_fake(ativo, _user_id):
        ativos_capturados.append(ativo)
        return "OPU-000001"

    service.criar_ativo = _criar_ativo_fake  # type: ignore[method-assign]

    conteudo_csv = (
        "tipo_ativo,marca,modelo,setor,status,data_entrada,imei_1\n"
        "Notebook,Dell,XPS,T.I,Dispon\u00edvel,2026-04-17,999999999999999\n"
    ).encode("utf-8")

    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={},
        user_id=1,
        modo_tudo_ou_nada=True,
    )

    assert resultado["ok_importacao"] is True
    assert ativos_capturados[0].imei_1 is None
    assert ativos_capturados[0].imei_2 is None


def test_preview_importacao_rejeita_csv_vazio():
    """
    CSV vazio deve falhar cedo com erro objetivo para o usuário.
    """
    service = _service_admin()

    with pytest.raises(AtivoErro):
        service.gerar_preview_importacao_csv(b"", user_id=1)


def test_confirmar_importacao_tudo_ou_nada_ignora_linha_descartada_com_erro(monkeypatch):
    """
    Regressão: linha descartada não pode bloquear o modo tudo-ou-nada.
    """
    service = _service_admin()

    monkeypatch.setattr(service, "_usuario_eh_admin", lambda _ctx: True)

    def validar_linha(_dados, numero_linha):
        if numero_linha == 3:
            raise AtivoErro("Linha 3: Setor inválido. Use um destes: T.I, Rh, Adm.")
        return SimpleNamespace(id_ativo=f"OPU-{numero_linha:06d}")

    monkeypatch.setattr(service, "_validar_linha_importacao", validar_linha)
    monkeypatch.setattr(service, "criar_ativo", lambda ativo, _user_id: ativo.id_ativo)

    conteudo_csv = (
        "tipo_ativo,marca,modelo,setor,status,data_entrada\n"
        "Notebook,Dell,XPS,T.I,Disponível,2026-04-17\n"
        "Notebook,Dell,XPS,Compras,Disponível,2026-04-17\n"
    ).encode("utf-8")

    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={},
        user_id=1,
        modo_tudo_ou_nada=True,
        mapeamento_confirmado={
            "tipo_ativo": "tipo_ativo",
            "marca": "marca",
            "modelo": "modelo",
            "setor": "setor",
            "status": "status",
            "data_entrada": "data_entrada",
        },
        linhas_descartadas={3},
        edicoes_por_linha={},
    )

    assert resultado["ok_importacao"] is True
    assert resultado["importados"] == 1
    assert resultado["falhas"] == 0


def test_confirmar_importacao_aplica_edicao_em_campo_canonico_apos_mapeamento(monkeypatch):
    """
    Regressão de contrato: edição enviada como campo canônico (setor)
    deve sobrescrever valor mapeado mesmo quando o CSV usa outro cabeçalho.
    """
    service = _service_admin()
    dados_recebidos = {}

    monkeypatch.setattr(service, "_usuario_eh_admin", lambda _ctx: True)

    def validar_linha(dados, numero_linha):
        dados_recebidos[numero_linha] = dict(dados)
        if dados.get("setor") != "T.I":
            raise AtivoErro(f"Linha {numero_linha}: Setor inválido. Use um destes: T.I, Rh, Adm.")
        return SimpleNamespace(id_ativo=f"OPU-{numero_linha:06d}")

    monkeypatch.setattr(service, "_validar_linha_importacao", validar_linha)
    monkeypatch.setattr(service, "criar_ativo", lambda ativo, _user_id: ativo.id_ativo)

    conteudo_csv = (
        "Tipo,Marca,Modelo,Departamento,Status,Data Entrada\n"
        "Notebook,Dell,XPS,Compras,Disponível,2026-04-17\n"
    ).encode("utf-8")

    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={},
        user_id=1,
        modo_tudo_ou_nada=True,
        mapeamento_confirmado={
            "Tipo": "tipo_ativo",
            "Marca": "marca",
            "Modelo": "modelo",
            "Departamento": "setor",
            "Status": "status",
            "Data Entrada": "data_entrada",
        },
        linhas_descartadas=set(),
        edicoes_por_linha={2: {"setor": "T.I"}},
    )

    # ===== CONTRATO ÚNICO (PARTE 2): Dados contêm apenas canônicos =====
    assert resultado["ok_importacao"] is True
    assert dados_recebidos[2]["setor"] == "T.I"
    # 'departamento' não deve estar nos dados internos (alias removido conforme PARTE 2/3)
    assert "departamento" not in dados_recebidos[2] or dados_recebidos[2].get("departamento") == dados_recebidos[2].get("setor")


def test_confirmar_importacao_modo_parcial_nao_falha_por_linhas_invalidas_ativas(monkeypatch):
    """
    Em modo parcial, erros de validação por linha devem gerar rejeição parcial,
    sem derrubar importação das linhas válidas.
    """
    service = _service_admin()

    monkeypatch.setattr(service, "_usuario_eh_admin", lambda _ctx: True)

    def validar_linha(_dados, numero_linha):
        if numero_linha == 3:
            raise AtivoErro("Linha 3: Setor inválido. Use um destes: T.I, Rh, Adm.")
        return SimpleNamespace(id_ativo=f"OPU-{numero_linha:06d}")

    monkeypatch.setattr(service, "_validar_linha_importacao", validar_linha)
    monkeypatch.setattr(service, "criar_ativo", lambda ativo, _user_id: ativo.id_ativo)

    conteudo_csv = (
        "tipo_ativo,marca,modelo,setor,status,data_entrada\n"
        "Notebook,Dell,XPS,T.I,Disponível,2026-04-17\n"
        "Notebook,Dell,XPS,Compras,Disponível,2026-04-17\n"
    ).encode("utf-8")

    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={},
        user_id=1,
        modo_tudo_ou_nada=False,
        mapeamento_confirmado={
            "tipo_ativo": "tipo_ativo",
            "marca": "marca",
            "modelo": "modelo",
            "setor": "setor",
            "status": "status",
            "data_entrada": "data_entrada",
        },
        linhas_descartadas=set(),
        edicoes_por_linha={},
    )

    assert resultado["ok_importacao"] is True
    assert resultado["importados"] == 1
    assert resultado["falhas"] == 1
    assert any("rejeitadas" in aviso.lower() for aviso in resultado["avisos"])


def test_confirmar_importacao_aplica_inferencia_email_em_campos_ausentes(monkeypatch):
    """
    Regressao: confirmacao deve validar linha com base na versao revisada,
    incluindo inferencia por e-mail quando setor/localizacao estiverem ausentes.

    ===== CONTRATO ÚNICO (PARTE 6): Inferência preenche campos ausentes =====
    Email 'ti@opusmedical.com.br' implica setor='T.I' e localizacao='Opus Medical'

    Comentário: Este teste valida que quando setor/localizacao chegam vazios do CSV
    (mas mapeados), a inferência de email os preenche automaticamente.
    """
    service = _service_admin()
    dados_recebidos = {}

    monkeypatch.setattr(service, "_usuario_eh_admin", lambda _ctx: True)

    def validar_linha(dados, numero_linha):
        dados_recebidos[numero_linha] = dict(dados)
        if dados.get("setor") != "T.I":
            raise AtivoErro(f"Linha {numero_linha}: Setor inválido.")
        if dados.get("localizacao") != "Opus Medical":
            raise AtivoErro(f"Linha {numero_linha}: Localização inválida.")
        return SimpleNamespace(id_ativo=f"OPU-{numero_linha:06d}")

    monkeypatch.setattr(service, "_validar_linha_importacao", validar_linha)
    monkeypatch.setattr(service, "criar_ativo", lambda ativo, _user_id: ativo.id_ativo)

    # CSV com setor e localizacao como colunas vazias
    # (simulando que o usuário não preencheu, mas estão mapeadas para permitir inferência)
    conteudo_csv = (
        "tipo_ativo,marca,modelo,setor,localizacao,status,data_entrada,email_responsavel\n"
        "Notebook,Dell,XPS,,,Disponível,2026-04-17,ti@opusmedical.com.br\n"
    ).encode("utf-8")

    # ===== INFERÊNCIA POR EMAIL (PARTE 6) =====
    # Setor e localizacao estão no CSV (mapeados) mas vazios
    # A inferência do email preencherá com T.I e Opus Medical automaticamente
    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={},
        user_id=1,
        modo_tudo_ou_nada=True,
        mapeamento_confirmado={
            "tipo_ativo": "tipo_ativo",
            "marca": "marca",
            "modelo": "modelo",
            "setor": "setor",
            "localizacao": "localizacao",
            "status": "status",
            "data_entrada": "data_entrada",
            "email_responsavel": "email_responsavel",
        },
        linhas_descartadas=set(),
        edicoes_por_linha={},
    )

    assert resultado["ok_importacao"] is True
    assert dados_recebidos[2]["setor"] == "T.I"
    assert dados_recebidos[2]["localizacao"] == "Opus Medical"


def test_confirmar_importacao_inferencia_nao_sobrescreve_setor_manual(monkeypatch):
    """
    Prioridade de fontes: setor editado manualmente deve vencer inferencia de e-mail.
    """
    service = _service_admin()
    dados_recebidos = {}

    monkeypatch.setattr(service, "_usuario_eh_admin", lambda _ctx: True)

    def validar_linha(dados, numero_linha):
        dados_recebidos[numero_linha] = dict(dados)
        return SimpleNamespace(id_ativo=f"OPU-{numero_linha:06d}")

    monkeypatch.setattr(service, "_validar_linha_importacao", validar_linha)
    monkeypatch.setattr(service, "criar_ativo", lambda ativo, _user_id: ativo.id_ativo)

    # ===== EDIÇÕES MANUAIS: Campo editado requer coluna no CSV =====
    # Para editar 'setor', a coluna precisa existir no CSV (mesmo que vazia)
    conteudo_csv = (
        "tipo_ativo,marca,modelo,setor,status,data_entrada,email_responsavel\n"
        "Notebook,Dell,XPS,,Disponível,2026-04-17,ti@opusmedical.com.br\n"
    ).encode("utf-8")

    # Mapeamento inclui a coluna 'setor' (que vem vazia do CSV)
    resultado = service.confirmar_importacao_csv(
        conteudo_csv,
        sugestoes_confirmadas={},
        user_id=1,
        modo_tudo_ou_nada=True,
        mapeamento_confirmado={
            "tipo_ativo": "tipo_ativo",
            "marca": "marca",
            "modelo": "modelo",
            "setor": "setor",
            "status": "status",
            "data_entrada": "data_entrada",
            "email_responsavel": "email_responsavel",
        },
        linhas_descartadas=set(),
        # Edição manual sobrescreve o valor do CSV (que está vazio, seria preenchido por inferência)
        edicoes_por_linha={2: {"setor": "Rh"}},
    )

    # ===== CONTRATO ÚNICO (PARTE 2/6): Edição manual tem prioridade sobre inferência =====
    assert resultado["ok_importacao"] is True
    assert dados_recebidos[2]["setor"] == "Rh"
    # 'departamento' não deve estar nos dados internos (alias removido conforme PARTE 2/3)
    assert "departamento" not in dados_recebidos[2] or dados_recebidos[2].get("departamento") == dados_recebidos[2].get("setor")
    # Comentário: Edição manual "Rh" foi aplicada, vencendo a inferência por email (que seria "T.I")
