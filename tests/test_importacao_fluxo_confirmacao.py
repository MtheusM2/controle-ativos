"""
Testes de regressão para o fluxo de confirmação da importação flexível.

Cobrem:
- preview expondo contadores consistentes
- confirmação usando a mesma estrutura de mapeamento
- retorno da primeira falha real em cenários all-or-nothing
- sucesso quando o payload está completo
"""

from types import SimpleNamespace

import pytest

from services.ativos_service import AtivosService, AtivoErro
from services.importacao_service_seguranca import ServicoImportacaoComSeguranca
from utils.import_mapper import ResultadoMatch


class FakeBaseImportacao:
    def processar_arquivo_csv(self, _conteudo_csv, _delimitador=None):
        _ = (_conteudo_csv, _delimitador)
        headers = ["tipo ativo", "marca", "modelo", "setor", "status", "data entrada"]
        linhas = [
            (2, {"tipo ativo": "Notebook", "marca": "Dell", "modelo": "Latitude", "setor": "TI", "status": "Em Uso", "data entrada": "2026-01-15"}),
            (3, {"tipo ativo": "Desktop", "marca": "Lenovo", "modelo": "ThinkCentre", "setor": "TI", "status": "Em Uso", "data entrada": "2026-01-16"}),
        ]
        metadados = SimpleNamespace(
            hash_arquivo="hash-test",
            delimitador=",",
            numero_linha_cabecalho=1,
            score_deteccao_cabecalho=0.99,
        )
        return headers, linhas, metadados

    def fazer_mapeamento(self, _headers):
        _ = _headers
        matches = [
            ResultadoMatch(
                coluna_origem="tipo ativo",
                campo_destino="tipo_ativo",
                score=0.95,
                estrategia="sinonimo",
                motivo="Match por normalização",
            ),
            ResultadoMatch(
                coluna_origem="marca",
                campo_destino="marca",
                score=1.0,
                estrategia="exata",
                motivo="Match exato",
            ),
            ResultadoMatch(
                coluna_origem="modelo",
                campo_destino="modelo",
                score=1.0,
                estrategia="exata",
                motivo="Match exato",
            ),
            ResultadoMatch(
                coluna_origem="setor",
                campo_destino="setor",
                score=1.0,
                estrategia="exata",
                motivo="Match exato",
            ),
            ResultadoMatch(
                coluna_origem="status",
                campo_destino="status",
                score=1.0,
                estrategia="exata",
                motivo="Match exato",
            ),
            ResultadoMatch(
                coluna_origem="data entrada",
                campo_destino="data_entrada",
                score=0.95,
                estrategia="sinonimo",
                motivo="Match por sinônimo",
            ),
        ]
        return SimpleNamespace(
            matches=matches,
            mapeamentos_altos=matches[:4],
            mapeamentos_medios=matches[4:],
            mapeamentos_baixos=[],
            campos_ignorados=[],
            campos_criticos_faltantes=[],
            duplicatas={},
            metadados=None,
        )

    def gerar_preview_estruturado(self, _resultado_mapeamento, primeiras_linhas=None, max_linhas_preview=5):
        _ = (_resultado_mapeamento, primeiras_linhas, max_linhas_preview)
        return {
            "colunas": {
                "exatas": [
                    {"coluna_origem": "tipo ativo", "campo_destino": "tipo_ativo"},
                    {"coluna_origem": "marca", "campo_destino": "marca"},
                ],
                "sugeridas": [
                    {"coluna_origem": "data entrada", "campo_sugerido": "data_entrada"},
                ],
                "ignoradas": [],
            },
            "preview_linhas": [
                {"linha": 2, "dados_originais": {"tipo ativo": "Notebook"}},
                {"linha": 3, "dados_originais": {"tipo ativo": "Desktop"}},
            ],
            "resumo_validacao": {
                "total_linhas": 2,
                "linhas_validas": 2,
                "linhas_invalidas": 0,
                "erros": [],
                "avisos": [],
            },
            "avisos": [],
            "metadados": {
                "delimitador": ",",
                "numero_linha_cabecalho": 1,
                "score_deteccao_cabecalho": 0.99,
                "hash_arquivo": "hash-test",
            },
        }


class FakeValidacaoLote:
    def __init__(self, total_linhas=2, linhas_validas=2, linhas_com_erro=0, linhas_com_aviso=0, taxa_erro_percentual=0.0, bloqueios=None, alertas=None):
        self.total_linhas = total_linhas
        self.linhas_validas = linhas_validas
        self.linhas_com_erro = linhas_com_erro
        self.linhas_com_aviso = linhas_com_aviso
        self.taxa_erro_percentual = taxa_erro_percentual
        self.bloqueios = bloqueios or []
        self.alertas = alertas or []


@pytest.fixture()
def preview_importacao_service(monkeypatch):
    servico = ServicoImportacaoComSeguranca()
    servico.servico_base = FakeBaseImportacao()
    servico.validador_lote.validar_lote = lambda **kwargs: FakeValidacaoLote()

    monkeypatch.setattr("services.importacao_service_seguranca.AuditoriaImportacaoService.iniciar_auditoria", lambda **kwargs: "IMP-TEST")
    monkeypatch.setattr("services.importacao_service_seguranca.AuditoriaImportacaoService.obter_usuarios_validos", lambda empresa_id: {"João"})
    monkeypatch.setattr("services.importacao_service_seguranca.AuditoriaImportacaoService.detectar_duplicatas", lambda ids_csv, empresa_id: {})
    monkeypatch.setattr("services.importacao_service_seguranca.AuditoriaImportacaoService.detectar_seriais_duplicados", lambda seriais_csv, empresa_id: {})
    monkeypatch.setattr("services.importacao_service_seguranca.AuditoriaImportacaoService.registrar_preview_gerado", lambda **kwargs: None)
    return servico


def test_preview_seguro_expoe_contadores_consistentes(preview_importacao_service):
    id_lote, preview = preview_importacao_service.gerar_preview_seguro(
        conteudo_csv=b"csv-bytes",
        usuario_id=1,
        empresa_id=10,
        endereco_ip="127.0.0.1",
        user_agent="pytest",
    )

    assert id_lote == "IMP-TEST"
    assert preview["validacao_detalhes"]["total_linhas"] == 2
    assert preview["validacao_detalhes"]["linhas_validas"] == 2
    assert preview["validacao_detalhes"]["linhas_invalidas"] == 0
    assert preview["resumo_analise"]["total_linhas"] == 2
    assert preview["resumo_analise"]["linhas_validas"] == 2
    assert preview["resumo_analise"]["linhas_invalidas"] == 0
    assert preview["metadados_auditoria"]["id_lote"] == "IMP-TEST"


def test_confirmar_importacao_csv_retorna_primeiro_erro_real(monkeypatch):
    servico = AtivosService()

    monkeypatch.setattr(servico, "_obter_contexto_acesso", lambda user_id: {"perfil": "admin", "empresa_id": 10})
    monkeypatch.setattr(servico, "_usuario_eh_admin", lambda contexto: True)
    monkeypatch.setattr(servico, "_fazer_classificacao_inteligente", lambda headers: {
        "exatas": [
            {"coluna_origem": "tipo ativo", "campo_destino": "tipo_ativo", "score": 1.0},
            {"coluna_origem": "marca", "campo_destino": "marca", "score": 1.0},
            {"coluna_origem": "modelo", "campo_destino": "modelo", "score": 1.0},
            {"coluna_origem": "setor", "campo_destino": "setor", "score": 1.0},
            {"coluna_origem": "status", "campo_destino": "status", "score": 1.0},
            {"coluna_origem": "data entrada", "campo_destino": "data_entrada", "score": 1.0},
        ],
        "sugeridas": [],
        "ignoradas": [],
        "mapeamento_exato": {
            "tipo ativo": "tipo_ativo",
            "marca": "marca",
            "modelo": "modelo",
            "setor": "setor",
            "status": "status",
            "data entrada": "data_entrada",
        },
    })
    monkeypatch.setattr(servico, "_extrair_mapeamento_exato", lambda classificacao: classificacao["mapeamento_exato"])
    monkeypatch.setattr(servico, "_resolver_mapeamento_confirmado", lambda classificacao, sugestoes: (classificacao["mapeamento_exato"], []))

    chamadas = {"count": 0}

    def validar_linha(_dados, numero_linha):
        _ = _dados
        chamadas["count"] += 1
        raise AtivoErro(f"Linha {numero_linha}: Setor inválido. Use um destes: T.I, Rh, Adm.")

    monkeypatch.setattr(servico, "_validar_linha_importacao", validar_linha)
    monkeypatch.setattr(servico, "criar_ativo", lambda ativo, user_id: "OPU-000001")

    resultado = servico.confirmar_importacao_csv(
        conteudo_csv=(
            b"tipo ativo,marca,modelo,setor,status,data entrada\n"
            b"Notebook,Dell,Latitude,Compras,Em Uso,2026-01-15\n"
        ),
        sugestoes_confirmadas={"tipo ativo": "tipo_ativo"},
        user_id=1,
        modo_tudo_ou_nada=True,
    )

    assert chamadas["count"] == 1
    assert resultado["ok_importacao"] is False
    assert resultado["falhas"] == 1
    assert resultado["importados"] == 0
    assert resultado["erros"][0].startswith("Linha 2: Setor inválido")


def test_confirmar_importacao_csv_sucesso_com_payload_completo(monkeypatch):
    servico = AtivosService()

    monkeypatch.setattr(servico, "_obter_contexto_acesso", lambda user_id: {"perfil": "admin", "empresa_id": 10})
    monkeypatch.setattr(servico, "_usuario_eh_admin", lambda contexto: True)
    monkeypatch.setattr(servico, "_fazer_classificacao_inteligente", lambda headers: {
        "exatas": [
            {"coluna_origem": "tipo ativo", "campo_destino": "tipo_ativo", "score": 1.0},
            {"coluna_origem": "marca", "campo_destino": "marca", "score": 1.0},
            {"coluna_origem": "modelo", "campo_destino": "modelo", "score": 1.0},
            {"coluna_origem": "setor", "campo_destino": "setor", "score": 1.0},
            {"coluna_origem": "status", "campo_destino": "status", "score": 1.0},
            {"coluna_origem": "data entrada", "campo_destino": "data_entrada", "score": 1.0},
        ],
        "sugeridas": [],
        "ignoradas": [],
        "mapeamento_exato": {
            "tipo ativo": "tipo_ativo",
            "marca": "marca",
            "modelo": "modelo",
            "setor": "setor",
            "status": "status",
            "data entrada": "data_entrada",
        },
    })
    monkeypatch.setattr(servico, "_extrair_mapeamento_exato", lambda classificacao: classificacao["mapeamento_exato"])
    monkeypatch.setattr(servico, "_resolver_mapeamento_confirmado", lambda classificacao, sugestoes: (classificacao["mapeamento_exato"], []))
    monkeypatch.setattr(servico, "_validar_linha_importacao", lambda dados, numero_linha: SimpleNamespace(id_ativo=f"NTB-{numero_linha:03d}"))
    monkeypatch.setattr(servico, "criar_ativo", lambda ativo, user_id: ativo.id_ativo)

    resultado = servico.confirmar_importacao_csv(
        conteudo_csv=(
            b"tipo ativo,marca,modelo,setor,status,data entrada\n"
            b"Notebook,Dell,Latitude,TI,Em Uso,2026-01-15\n"
        ),
        sugestoes_confirmadas={"tipo ativo": "tipo_ativo"},
        user_id=1,
        modo_tudo_ou_nada=True,
    )

    assert resultado["ok_importacao"] is True
    assert resultado["falhas"] == 0
    assert resultado["importados"] == 1
    assert resultado["ids_criados"] == ["NTB-002"]


def test_confirmar_importacao_csv_bloqueia_payload_incompleto(monkeypatch):
    servico = AtivosService()

    monkeypatch.setattr(servico, "_obter_contexto_acesso", lambda user_id: {"perfil": "admin", "empresa_id": 10})
    monkeypatch.setattr(servico, "_usuario_eh_admin", lambda contexto: True)
    monkeypatch.setattr(servico, "_fazer_classificacao_inteligente", lambda headers: {
        "exatas": [
            {"coluna_origem": "tipo ativo", "campo_destino": "tipo_ativo", "score": 1.0},
        ],
        "sugeridas": [
            {"coluna_origem": "tipo ativo", "campo_sugerido": "tipo_ativo", "score": 0.95},
        ],
        "ignoradas": [],
        "mapeamento_exato": {},
    })
    monkeypatch.setattr(servico, "_extrair_mapeamento_exato", lambda classificacao: classificacao["mapeamento_exato"])
    monkeypatch.setattr(servico, "_resolver_mapeamento_confirmado", lambda classificacao, sugestoes: ({}, []))

    resultado = servico.confirmar_importacao_csv(
        conteudo_csv=(
            b"tipo ativo\n"
            b"Notebook\n"
        ),
        sugestoes_confirmadas={},
        user_id=1,
        modo_tudo_ou_nada=True,
    )

    assert resultado["ok_importacao"] is False
    assert resultado["falhas"] == 1
    assert "não foi confirmado" in resultado["erros"][0].lower()
