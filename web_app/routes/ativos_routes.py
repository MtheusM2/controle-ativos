from __future__ import annotations

import csv
import io
from pathlib import Path

from flask import jsonify, redirect, render_template, request, send_file, session, url_for

from models.ativos import Ativo
from services.ativos_arquivo_service import ArquivoNaoEncontrado, TipoDocumentoInvalido
from services.ativos_service import AtivoErro, AtivoNaoEncontrado, AtivosService, PermissaoNegada
from utils.validators import STATUS_VALIDOS


def _obter_user_id_logado() -> int | None:
    """
    Obtém o identificador do usuário autenticado na sessão.
    """
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return int(user_id)


def _request_data() -> dict:
    """
    Obtém o payload JSON ou o form-data da requisição.
    """
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def _json_success(message: str, *, status: int = 200, **payload):
    """
    Padroniza respostas JSON de sucesso.
    """
    body = {"ok": True, "mensagem": message}
    body.update(payload)
    return jsonify(body), status


def _json_error(message: str, status: int = 400, **payload):
    """
    Padroniza respostas JSON de erro.
    """
    body = {"ok": False, "erro": message}
    body.update(payload)
    return jsonify(body), status


def _normalizar_flag_presenca(raw_value: str | None) -> str | None:
    """
    Normaliza flags de presença recebidas no filtro (sim/nao).
    """
    value = (raw_value or "").strip().lower()
    if value in {"sim", "true", "1", "com"}:
        return "sim"
    if value in {"nao", "false", "0", "sem"}:
        return "nao"
    return None


def _serializar_ativo(ativo: Ativo) -> dict:
    """
    Serializa o ativo no contrato mínimo esperado pelo dashboard.
    """
    return {
        "id": ativo.id_ativo,
        "tipo": ativo.tipo,
        "marca": ativo.marca,
        "modelo": ativo.modelo,
        "usuario_responsavel": ativo.usuario_responsavel or "",
        "departamento": ativo.departamento or "",
        "status": ativo.status or "",
        "data_entrada": ativo.data_entrada or "",
        "data_saida": ativo.data_saida or "",
        # Usa getattr para manter compatibilidade com objetos de teste simplificados.
        "nota_fiscal": getattr(ativo, "nota_fiscal", "") or "",
        "garantia": getattr(ativo, "garantia", "") or "",
    }


def _serializar_arquivo(arquivo: dict) -> dict:
    """
    Serializa um registro de arquivo para o frontend.
    """
    return {
        "id": arquivo["id"],
        "ativo_id": arquivo["ativo_id"],
        "tipo_documento": arquivo["tipo_documento"],
        "nome_original": arquivo["nome_original"],
        "tamanho_bytes": arquivo["tamanho_bytes"],
        "mime_type": arquivo["mime_type"],
        "criado_em": arquivo["criado_em"],
    }


def _ativo_do_payload(dados: dict) -> Ativo:
    """
    Constrói o domínio Ativo a partir do payload do frontend.
    """
    return Ativo(
        id_ativo=dados.get("id", ""),
        tipo=dados.get("tipo", ""),
        marca=dados.get("marca", ""),
        modelo=dados.get("modelo", ""),
        usuario_responsavel=dados.get("usuario_responsavel", "") or None,
        departamento=dados.get("departamento", ""),
        status=dados.get("status", ""),
        data_entrada=dados.get("data_entrada", ""),
        data_saida=dados.get("data_saida", "") or None,
        nota_fiscal=None,
        garantia=None,
    )


def registrar_rotas_ativos(app, *, ativos_service: AtivosService, ativos_arquivo_service):
    """
    Registra a camada HTTP do dashboard e do CRUD mínimo de ativos.
    """
    service = ativos_service
    arquivo_service = ativos_arquivo_service

    def _coletar_filtros_e_ordenacao_da_query() -> tuple[dict, str, str, str | None, str | None]:
        """
        Centraliza leitura de query params para manter consistência entre lista e exportação.
        """
        filtros = {
            "id_ativo": request.args.get("id_ativo", "").strip() or None,
            "tipo": request.args.get("tipo", "").strip() or None,
            "marca": request.args.get("marca", "").strip() or None,
            "modelo": request.args.get("modelo", "").strip() or None,
            "usuario_responsavel": request.args.get("usuario_responsavel", "").strip() or None,
            "departamento": request.args.get("departamento", "").strip() or None,
            "nota_fiscal": request.args.get("nota_fiscal", "").strip() or None,
            "garantia": request.args.get("garantia", "").strip() or None,
            "status": request.args.get("status", "").strip() or None,
            "data_entrada_inicial": request.args.get("data_entrada_inicial", "").strip() or None,
            "data_entrada_final": request.args.get("data_entrada_final", "").strip() or None,
            "data_saida_inicial": request.args.get("data_saida_inicial", "").strip() or None,
            "data_saida_final": request.args.get("data_saida_final", "").strip() or None,
        }
        filtros = {k: v for k, v in filtros.items() if v is not None}

        ordenar_por = request.args.get("ordenar_por", "id").strip() or "id"
        ordem = request.args.get("ordem", "asc").strip().lower() or "asc"

        tem_garantia = _normalizar_flag_presenca(request.args.get("tem_garantia"))
        tem_nota_fiscal = _normalizar_flag_presenca(request.args.get("tem_nota_fiscal"))
        return filtros, ordenar_por, ordem, tem_garantia, tem_nota_fiscal

    def _filtrar_presenca_documentos(
        ativos: list[Ativo],
        *,
        tem_garantia: str | None,
        tem_nota_fiscal: str | None,
    ) -> list[Ativo]:
        """
        Aplica filtros de presença documental sem alterar regras de negócio da camada service.
        """
        filtrados = ativos

        if tem_garantia == "sim":
            filtrados = [a for a in filtrados if (a.garantia or "").strip()]
        elif tem_garantia == "nao":
            filtrados = [a for a in filtrados if not (a.garantia or "").strip()]

        if tem_nota_fiscal == "sim":
            filtrados = [a for a in filtrados if (a.nota_fiscal or "").strip()]
        elif tem_nota_fiscal == "nao":
            filtrados = [a for a in filtrados if not (a.nota_fiscal or "").strip()]

        return filtrados

    def _buscar_ativos_com_filtros(user_id: int) -> list[Ativo]:
        """
        Resolve listagem com reaproveitamento da API atual e filtros complementares de presença.
        """
        filtros, ordenar_por, ordem, tem_garantia, tem_nota_fiscal = _coletar_filtros_e_ordenacao_da_query()

        if filtros:
            ativos = service.filtrar_ativos(
                user_id=user_id,
                filtros=filtros,
                ordenar_por=ordenar_por,
                ordem=ordem,
            )
        else:
            ativos = service.listar_ativos(user_id)

        return _filtrar_presenca_documentos(
            ativos,
            tem_garantia=tem_garantia,
            tem_nota_fiscal=tem_nota_fiscal,
        )

    @app.get("/dashboard")
    def dashboard():
        """
        Tela principal do sistema após autenticação.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return redirect(url_for("home"))

        # Mantém o dashboard como visão geral com indicadores leves e atalhos.
        indicadores = {
            "total_ativos": 0,
            "total_em_uso": 0,
            "total_disponivel": 0,
            "total_baixado": 0,
        }
        try:
            ativos = service.listar_ativos(user_id)
            indicadores["total_ativos"] = len(ativos)
            indicadores["total_em_uso"] = sum(1 for a in ativos if (a.status or "").strip().lower() == "em uso")
            indicadores["total_disponivel"] = sum(1 for a in ativos if (a.status or "").strip().lower() == "disponível")
            indicadores["total_baixado"] = sum(1 for a in ativos if (a.status or "").strip().lower() == "baixado")
        except AtivoErro:
            # Em caso de falha de leitura, preserva renderização do dashboard sem interromper UX.
            pass

        return render_template(
            "dashboard.html",
            usuario_email=session.get("user_email"),
            status_validos=STATUS_VALIDOS,
            indicadores=indicadores,
            show_chrome=True,
        )

    @app.get("/ativos")
    def listar_ativos():
        """
        Lista os ativos do usuário autenticado em formato JSON.
        Aceita parâmetros de filtro opcionais.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return _json_error("Sessão expirada. Faça login novamente.", status=401)

        try:
            ativos = _buscar_ativos_com_filtros(user_id)

            return _json_success(
                "Ativos carregados com sucesso.",
                ativos=[_serializar_ativo(ativo) for ativo in ativos],
            )
        except AtivoErro as erro:
            return _json_error(str(erro), status=400)
        except (ValueError, KeyError, TypeError):
            return _json_error("Erro inesperado ao listar ativos.", status=500)

    @app.post("/ativos")
    def criar_ativo():
        """
        Cria um novo ativo usando o contrato mínimo do dashboard.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return _json_error("Sessão expirada. Faça login novamente.", status=401)

        try:
            ativo = _ativo_do_payload(_request_data())
            service.criar_ativo(ativo, user_id)
            criado = service.buscar_ativo(ativo.id_ativo, user_id)
            return _json_success(
                "Ativo cadastrado com sucesso.",
                status=201,
                ativo=_serializar_ativo(criado),
            )
        except AtivoErro as erro:
            return _json_error(str(erro), status=400)
        except (ValueError, KeyError, TypeError):
            return _json_error("Erro inesperado ao cadastrar ativo.", status=500)

    @app.get("/ativos/<id_ativo>")
    def buscar_ativo(id_ativo):
        """
        Retorna um ativo específico em JSON.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return _json_error("Sessão expirada. Faça login novamente.", status=401)

        try:
            ativo = service.buscar_ativo(id_ativo, user_id)
            return _json_success("Ativo carregado com sucesso.", ativo=_serializar_ativo(ativo))
        except AtivoNaoEncontrado as erro:
            return _json_error(str(erro), status=404)
        except (PermissaoNegada, AtivoErro) as erro:
            return _json_error(str(erro), status=400)
        except (ValueError, KeyError, TypeError):
            return _json_error("Erro inesperado ao consultar ativo.", status=500)

    @app.put("/ativos/<id_ativo>")
    def atualizar_ativo(id_ativo):
        """
        Atualiza um ativo específico via fetch.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return _json_error("Sessão expirada. Faça login novamente.", status=401)

        dados = _request_data()
        dados_normalizados = {
            "tipo": dados.get("tipo", ""),
            "marca": dados.get("marca", ""),
            "modelo": dados.get("modelo", ""),
            "usuario_responsavel": dados.get("usuario_responsavel", "") or None,
            "departamento": dados.get("departamento", ""),
            "status": dados.get("status", ""),
            "data_entrada": dados.get("data_entrada", ""),
            "data_saida": dados.get("data_saida", "") or None,
            "nota_fiscal": None,
            "garantia": None,
        }

        try:
            ativo = service.atualizar_ativo(id_ativo=id_ativo, dados=dados_normalizados, user_id=user_id)
            return _json_success("Ativo atualizado com sucesso.", ativo=_serializar_ativo(ativo))
        except AtivoNaoEncontrado as erro:
            return _json_error(str(erro), status=404)
        except (PermissaoNegada, AtivoErro) as erro:
            return _json_error(str(erro), status=400)
        except (ValueError, KeyError, TypeError):
            return _json_error("Erro inesperado ao atualizar ativo.", status=500)

    @app.delete("/ativos/<id_ativo>")
    def remover_ativo(id_ativo):
        """
        Exclui um ativo específico via fetch.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return _json_error("Sessão expirada. Faça login novamente.", status=401)

        try:
            service.remover_ativo(id_ativo, user_id)
            return _json_success("Ativo removido com sucesso.")
        except AtivoNaoEncontrado as erro:
            return _json_error(str(erro), status=404)
        except (PermissaoNegada, AtivoErro) as erro:
            return _json_error(str(erro), status=400)
        except (ValueError, KeyError, TypeError):
            return _json_error("Erro inesperado ao remover ativo.", status=500)

    @app.get("/ativos/lista")
    def listar_ativos_html():
        """
        Renderiza a listagem de ativos com filtros em modal e ações por linha.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return redirect(url_for("home"))

        return render_template(
            "ativos.html",
            usuario_email=session.get("user_email"),
            status_validos=STATUS_VALIDOS,
            show_chrome=True,
        )

    @app.get("/ativos/novo")
    def criar_ativo_html():
        """
        Renderiza tela dedicada de cadastro com seção de documentos vinculados ao ativo.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return redirect(url_for("home"))

        return render_template(
            "novo_ativo.html",
            usuario_email=session.get("user_email"),
            status_validos=STATUS_VALIDOS,
            show_chrome=True,
        )

    @app.get("/ativos/editar/<id_ativo>")
    def editar_ativo_html(id_ativo):
        """
        Renderiza tela dedicada de edição de ativo e gestão de documentos vinculados.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return redirect(url_for("home"))

        return render_template(
            "editar_ativo.html",
            usuario_email=session.get("user_email"),
            status_validos=STATUS_VALIDOS,
            id_ativo=id_ativo,
            read_only=False,
            show_chrome=True,
        )

    @app.get("/ativos/visualizar/<id_ativo>")
    def visualizar_ativo_html(id_ativo):
        """
        Renderiza visualização somente leitura para consulta rápida do ativo.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return redirect(url_for("home"))

        return render_template(
            "editar_ativo.html",
            usuario_email=session.get("user_email"),
            status_validos=STATUS_VALIDOS,
            id_ativo=id_ativo,
            read_only=True,
            show_chrome=True,
        )

    @app.post("/ativos/remover/<id_ativo>")
    def remover_ativo_html(id_ativo):
        """
        Mantém compatibilidade com remoções legadas em HTML.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return redirect(url_for("home"))

        try:
            service.remover_ativo(id_ativo, user_id)
        except AtivoErro:
            pass

        return redirect(url_for("listar_ativos_html"))

    # ====== ANEXOS (FILES) ======

    @app.post("/ativos/<id_ativo>/anexos")
    def upload_anexo(id_ativo):
        """
        Faz upload de um anexo para um ativo.
        Espera: type (nota_fiscal ou garantia), file (arquivo binário)
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return _json_error("Sessão expirada. Faça login novamente.", status=401)

        tipo_documento = request.form.get("type", "").strip()
        arquivo = request.files.get("file")

        if not arquivo:
            return _json_error("Nenhum arquivo foi enviado.", status=400)

        try:
            arquivo_id = arquivo_service.salvar_arquivo(
                ativo_id=id_ativo,
                tipo_documento=tipo_documento,
                arquivo=arquivo,
                user_id=user_id
            )
            return _json_success(
                "Anexo enviado com sucesso.",
                status=201,
                arquivo_id=arquivo_id
            )
        except (TipoDocumentoInvalido, ArquivoNaoEncontrado) as erro:
            return _json_error(str(erro), status=400)
        except AtivoErro as erro:
            return _json_error(str(erro), status=400)
        except Exception:
            return _json_error("Erro ao fazer upload do anexo.", status=500)

    @app.get("/ativos/<id_ativo>/anexos")
    def listar_anexos(id_ativo):
        """
        Lista os anexos de um ativo.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return _json_error("Sessão expirada. Faça login novamente.", status=401)

        try:
            arquivos = arquivo_service.listar_arquivos(id_ativo, user_id)
            return _json_success(
                "Anexos carregados com sucesso.",
                anexos=[_serializar_arquivo(arquivo) for arquivo in arquivos]
            )
        except AtivoErro as erro:
            return _json_error(str(erro), status=400)
        except Exception:
            return _json_error("Erro ao listar anexos.", status=500)

    @app.get("/anexos/<int:arquivo_id>/download")
    def download_anexo(arquivo_id):
        """
        Faz download de um anexo específico.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return _json_error("Sessão expirada. Faça login novamente.", status=401)

        try:
            arquivo = arquivo_service.obter_arquivo(arquivo_id, user_id)
            caminho_fisico = Path(arquivo_service.upload_base_dir) / arquivo["caminho_arquivo"]
            
            if not caminho_fisico.exists():
                return _json_error("Arquivo não encontrado no servidor.", status=404)
            
            return send_file(
                caminho_fisico,
                as_attachment=True,
                download_name=arquivo["nome_original"],
                mimetype=arquivo["mime_type"] or "application/octet-stream"
            )
        except ArquivoNaoEncontrado as erro:
            return _json_error(str(erro), status=404)
        except AtivoErro as erro:
            return _json_error(str(erro), status=400)
        except Exception:
            return _json_error("Erro ao fazer download.", status=500)

    @app.delete("/anexos/<int:arquivo_id>")
    def remover_anexo(arquivo_id):
        """
        Remove um anexo específico.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return _json_error("Sessão expirada. Faça login novamente.", status=401)

        try:
            arquivo_service.remover_arquivo(arquivo_id, user_id)
            return _json_success("Anexo removido com sucesso.")
        except ArquivoNaoEncontrado as erro:
            return _json_error(str(erro), status=404)
        except AtivoErro as erro:
            return _json_error(str(erro), status=400)
        except Exception:
            return _json_error("Erro ao remover anexo.", status=500)

    # ====== EXPORT / IMPORT ======

    @app.get("/ativos/export/csv")
    def exportar_ativos_csv():
        """
        Exporta a lista de ativos (com filtros opcionais) em formato CSV.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return _json_error("Sessão expirada. Faça login novamente.", status=401)

        try:
            ativos = _buscar_ativos_com_filtros(user_id)

            # Monta CSV em memória
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "id", "tipo", "marca", "modelo", "usuario_responsavel",
                    "departamento", "status", "data_entrada", "data_saida",
                    "nota_fiscal", "garantia"
                ]
            )
            writer.writeheader()
            
            for ativo in ativos:
                writer.writerow({
                    "id": ativo.id_ativo,
                    "tipo": ativo.tipo,
                    "marca": ativo.marca,
                    "modelo": ativo.modelo,
                    "usuario_responsavel": ativo.usuario_responsavel or "",
                    "departamento": ativo.departamento or "",
                    "status": ativo.status or "",
                    "data_entrada": ativo.data_entrada or "",
                    "data_saida": ativo.data_saida or "",
                    "nota_fiscal": ativo.nota_fiscal or "",
                    "garantia": ativo.garantia or "",
                })
            
            csv_bytes = io.BytesIO(output.getvalue().encode("utf-8-sig"))
            
            return send_file(
                csv_bytes,
                as_attachment=True,
                download_name="ativos_export.csv",
                mimetype="text/csv"
            )
        except AtivoErro as erro:
            return _json_error(str(erro), status=400)
        except Exception:
            return _json_error("Erro ao exportar ativos.", status=500)

    @app.get("/ativos/export/<formato>")
    def exportar_ativos(formato: str):
        """
        Estrutura extensível de exportação com fallback seguro para CSV.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return _json_error("Sessão expirada. Faça login novamente.", status=401)

        formato_normalizado = (formato or "").strip().lower()

        if formato_normalizado in {"csv", "xlsx", "xls", "pdf"}:
            # Mantém fallback em CSV para formatos ainda não implementados no backend.
            return exportar_ativos_csv()

        if formato_normalizado == "json":
            try:
                ativos = _buscar_ativos_com_filtros(user_id)
                return jsonify(
                    {
                        "ok": True,
                        "formato": "json",
                        "total": len(ativos),
                        "ativos": [_serializar_ativo(ativo) for ativo in ativos],
                    }
                )
            except AtivoErro as erro:
                return _json_error(str(erro), status=400)
            except Exception:
                return _json_error("Erro ao exportar ativos.", status=500)

        return _json_error("Formato de exportação não suportado.", status=400)

    @app.post("/ativos/import/csv")
    def importar_ativos_csv():
        """
        Importa ativos a partir de um arquivo CSV.
        Esperado: file (arquivo CSV com headers: id, tipo, marca, modelo, etc)
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return _json_error("Sessão expirada. Faça login novamente.", status=401)

        arquivo = request.files.get("file")
        if not arquivo:
            return _json_error("Nenhum arquivo foi enviado.", status=400)

        try:
            # Lê o arquivo CSV
            stream = io.TextIOWrapper(arquivo.stream, encoding="utf-8")
            reader = csv.DictReader(stream)
            
            if not reader.fieldnames:
                return _json_error("Arquivo CSV vazio ou inválido.", status=400)
            
            criados = 0
            erros = []
            
            for idx, row in enumerate(reader, start=2):  # start=2 pois header é linha 1
                try:
                    ativo = Ativo(
                        id_ativo=row.get("id", "").strip(),
                        tipo=row.get("tipo", "").strip(),
                        marca=row.get("marca", "").strip(),
                        modelo=row.get("modelo", "").strip(),
                        usuario_responsavel=row.get("usuario_responsavel", "").strip() or None,
                        departamento=row.get("departamento", "").strip(),
                        status=row.get("status", "").strip(),
                        data_entrada=row.get("data_entrada", "").strip(),
                        data_saida=row.get("data_saida", "").strip() or None,
                        nota_fiscal=row.get("nota_fiscal", "").strip() or None,
                        garantia=row.get("garantia", "").strip() or None,
                    )
                    service.criar_ativo(ativo, user_id)
                    criados += 1
                except AtivoErro as e:
                    erros.append(f"Linha {idx}: {str(e)}")
                except Exception as e:
                    erros.append(f"Linha {idx}: Erro inesperado - {str(e)}")
            
            msg = f"Importação concluída: {criados} ativo(s) criado(s)."
            if erros:
                msg += f" {len(erros)} erro(s)."
            
            return _json_success(
                msg,
                status=201,
                criados=criados,
                erros=erros if erros else None
            )
        except Exception:
            return _json_error("Erro ao processar arquivo CSV.", status=500)
