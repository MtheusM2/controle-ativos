# web_app/routes/ativos_routes.py

# Rotas web do módulo de ativos.
# Esta camada deve:
# - receber dados da interface
# - chamar os services
# - renderizar templates
# A regra de negócio permanece nos services e validators.

from pathlib import Path

from flask import (
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file
)

from services.ativos_service import AtivosService, AtivoErro
from services.ativos_arquivo_service import (
    AtivosArquivoService,
    AtivoArquivoErro
)
from models.ativos import Ativo
from utils.validators import STATUS_VALIDOS


def _obter_user_id_logado() -> int | None:
    """
    Obtém o ID do usuário autenticado a partir da sessão.
    """
    user_id = session.get("user_id")

    if user_id is None:
        return None

    return int(user_id)


def registrar_rotas_ativos(app):
    """
    Registra as rotas web relacionadas aos ativos.
    """
    service = AtivosService()

    def _arquivo_service() -> AtivosArquivoService:
        """
        Cria o service de anexos usando a configuração da aplicação.
        """
        return AtivosArquivoService(current_app.config["UPLOAD_FOLDER"])

    @app.route("/ativos")
    def listar_ativos():
        """
        Lista ou filtra os ativos do usuário autenticado.
        """
        user_id = _obter_user_id_logado()

        if user_id is None:
            return redirect(url_for("login"))

        try:
            # Captura filtros da URL.
            filtros = {
                "id_ativo": request.args.get("id_ativo", "").strip() or None,
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

            ordenar_por = request.args.get("ordenar_por", "id").strip() or "id"
            ordem = request.args.get("ordem", "asc").strip().lower() or "asc"

            # Detecta se algum filtro foi realmente enviado.
            ha_filtro = any(valor for valor in filtros.values()) or ordenar_por != "id" or ordem != "asc"

            if ha_filtro:
                ativos = service.filtrar_ativos(
                    user_id=user_id,
                    filtros=filtros,
                    ordenar_por=ordenar_por,
                    ordem=ordem
                )
            else:
                ativos = service.listar_ativos(user_id)

            ativos_dict = [ativo.to_dict() for ativo in ativos]

            # Conta anexos por ativo para exibir na listagem.
            ativo_ids = [ativo["id_ativo"] for ativo in ativos_dict]
            contagem_anexos = _arquivo_service().contar_por_ativo(ativo_ids, user_id)

            for ativo in ativos_dict:
                ativo["total_anexos"] = contagem_anexos.get(ativo["id_ativo"], 0)

            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=None,
                usuario_email=session.get("user_email"),
                status_validos=STATUS_VALIDOS,
                filtros=request.args,
                ordenar_por=ordenar_por,
                ordem=ordem
            )

        except Exception as erro:
            return render_template(
                "ativos.html",
                ativos=[],
                erro=f"Erro ao listar ativos: {erro}",
                usuario_email=session.get("user_email"),
                status_validos=STATUS_VALIDOS,
                filtros=request.args,
                ordenar_por=request.args.get("ordenar_por", "id"),
                ordem=request.args.get("ordem", "asc")
            )

    @app.route("/ativos/novo", methods=["GET", "POST"])
    def criar_ativo():
        """
        Exibe e processa o cadastro de um novo ativo.
        """
        user_id = _obter_user_id_logado()

        if user_id is None:
            return redirect(url_for("login"))

        if request.method == "POST":
            dados = request.form.to_dict()

            try:
                ativo = Ativo(
                    id_ativo=dados.get("id", ""),
                    tipo=dados.get("tipo", ""),
                    marca=dados.get("marca", ""),
                    modelo=dados.get("modelo", ""),
                    usuario_responsavel=dados.get("usuario_responsavel", "") or None,
                    departamento=dados.get("departamento", ""),
                    nota_fiscal=dados.get("nota_fiscal", "") or None,
                    garantia=dados.get("garantia", "") or None,
                    status=dados.get("status", ""),
                    data_entrada=dados.get("data_entrada", ""),
                    data_saida=dados.get("data_saida", "") or None
                )

                service.criar_ativo(ativo, user_id)

                return redirect(url_for("listar_ativos"))

            except AtivoErro as erro:
                return render_template(
                    "novo_ativo.html",
                    erro=str(erro),
                    dados=dados,
                    status_validos=STATUS_VALIDOS,
                    usuario_email=session.get("user_email")
                )

            except Exception as erro:
                return render_template(
                    "novo_ativo.html",
                    erro=f"Erro inesperado ao cadastrar ativo: {erro}",
                    dados=dados,
                    status_validos=STATUS_VALIDOS,
                    usuario_email=session.get("user_email")
                )

        return render_template(
            "novo_ativo.html",
            erro=None,
            dados=None,
            status_validos=STATUS_VALIDOS,
            usuario_email=session.get("user_email")
        )

    @app.route("/ativos/editar/<id_ativo>", methods=["GET", "POST"])
    def editar_ativo(id_ativo):
        """
        Exibe e processa a edição de um ativo existente.
        """
        user_id = _obter_user_id_logado()

        if user_id is None:
            return redirect(url_for("login"))

        if request.method == "POST":
            dados = request.form.to_dict()

            try:
                if "usuario_responsavel" in dados and not dados["usuario_responsavel"].strip():
                    dados["usuario_responsavel"] = None

                if "nota_fiscal" in dados and not dados["nota_fiscal"].strip():
                    dados["nota_fiscal"] = None

                if "garantia" in dados and not dados["garantia"].strip():
                    dados["garantia"] = None

                if "data_saida" in dados and not dados["data_saida"].strip():
                    dados["data_saida"] = None

                service.atualizar_ativo(
                    id_ativo=id_ativo,
                    dados=dados,
                    user_id=user_id
                )

                return redirect(url_for("editar_ativo", id_ativo=id_ativo))

            except AtivoErro as erro:
                arquivos = _arquivo_service().listar_arquivos(id_ativo, user_id)

                return render_template(
                    "editar_ativo.html",
                    erro=str(erro),
                    dados=dados,
                    arquivos=arquivos,
                    id_ativo=id_ativo,
                    status_validos=STATUS_VALIDOS,
                    usuario_email=session.get("user_email")
                )

            except Exception as erro:
                arquivos = _arquivo_service().listar_arquivos(id_ativo, user_id)

                return render_template(
                    "editar_ativo.html",
                    erro=f"Erro inesperado ao editar ativo: {erro}",
                    dados=dados,
                    arquivos=arquivos,
                    id_ativo=id_ativo,
                    status_validos=STATUS_VALIDOS,
                    usuario_email=session.get("user_email")
                )

        try:
            ativo = service.buscar_ativo(id_ativo, user_id)
            dados = ativo.to_dict()
            arquivos = _arquivo_service().listar_arquivos(id_ativo, user_id)

            return render_template(
                "editar_ativo.html",
                erro=None,
                dados=dados,
                arquivos=arquivos,
                id_ativo=id_ativo,
                status_validos=STATUS_VALIDOS,
                usuario_email=session.get("user_email")
            )

        except AtivoErro as erro:
            ativos = service.listar_ativos(user_id)
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=str(erro),
                usuario_email=session.get("user_email"),
                status_validos=STATUS_VALIDOS,
                filtros={},
                ordenar_por="id",
                ordem="asc"
            )

        except Exception as erro:
            ativos = service.listar_ativos(user_id)
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=f"Erro inesperado ao carregar ativo para edição: {erro}",
                usuario_email=session.get("user_email"),
                status_validos=STATUS_VALIDOS,
                filtros={},
                ordenar_por="id",
                ordem="asc"
            )

    @app.route("/ativos/<id_ativo>/arquivos/upload", methods=["POST"])
    def upload_arquivo_ativo(id_ativo):
        """
        Faz upload de um novo anexo para o ativo.
        """
        user_id = _obter_user_id_logado()

        if user_id is None:
            return redirect(url_for("login"))

        tipo_documento = request.form.get("tipo_documento", "")
        arquivo = request.files.get("arquivo")

        try:
            _arquivo_service().salvar_arquivo(
                ativo_id=id_ativo,
                tipo_documento=tipo_documento,
                arquivo=arquivo,
                user_id=user_id
            )
            return redirect(url_for("editar_ativo", id_ativo=id_ativo))

        except (AtivoArquivoErro, AtivoErro) as erro:
            try:
                ativo = service.buscar_ativo(id_ativo, user_id)
                dados = ativo.to_dict()
                arquivos = _arquivo_service().listar_arquivos(id_ativo, user_id)
            except Exception:
                dados = {}
                arquivos = []

            return render_template(
                "editar_ativo.html",
                erro=str(erro),
                dados=dados,
                arquivos=arquivos,
                id_ativo=id_ativo,
                status_validos=STATUS_VALIDOS,
                usuario_email=session.get("user_email")
            )

    @app.route("/ativos/arquivos/<int:arquivo_id>/download")
    def download_arquivo_ativo(arquivo_id):
        """
        Faz download controlado de um anexo do ativo.
        """
        user_id = _obter_user_id_logado()

        if user_id is None:
            return redirect(url_for("login"))

        try:
            arquivo = _arquivo_service().obter_arquivo(arquivo_id, user_id)
            caminho_fisico = Path(current_app.config["UPLOAD_FOLDER"]) / arquivo["caminho_arquivo"]

            return send_file(
                caminho_fisico,
                as_attachment=True,
                download_name=arquivo["nome_original"]
            )

        except (AtivoArquivoErro, AtivoErro) as erro:
            ativos = service.listar_ativos(user_id)
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=str(erro),
                usuario_email=session.get("user_email"),
                status_validos=STATUS_VALIDOS,
                filtros={},
                ordenar_por="id",
                ordem="asc"
            )

    @app.route("/ativos/arquivos/<int:arquivo_id>/remover", methods=["POST"])
    def remover_arquivo_ativo(arquivo_id):
        """
        Remove um anexo do ativo.
        """
        user_id = _obter_user_id_logado()

        if user_id is None:
            return redirect(url_for("login"))

        try:
            arquivo = _arquivo_service().obter_arquivo(arquivo_id, user_id)
            ativo_id = arquivo["ativo_id"]

            _arquivo_service().remover_arquivo(arquivo_id, user_id)

            return redirect(url_for("editar_ativo", id_ativo=ativo_id))

        except (AtivoArquivoErro, AtivoErro) as erro:
            ativos = service.listar_ativos(user_id)
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=str(erro),
                usuario_email=session.get("user_email"),
                status_validos=STATUS_VALIDOS,
                filtros={},
                ordenar_por="id",
                ordem="asc"
            )

    @app.route("/ativos/remover/<id_ativo>", methods=["POST"])
    def remover_ativo(id_ativo):
        """
        Remove um ativo existente.
        """
        user_id = _obter_user_id_logado()

        if user_id is None:
            return redirect(url_for("login"))

        try:
            service.remover_ativo(id_ativo, user_id)

            return redirect(url_for("listar_ativos"))

        except AtivoErro as erro:
            ativos = service.listar_ativos(user_id)
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=str(erro),
                usuario_email=session.get("user_email"),
                status_validos=STATUS_VALIDOS,
                filtros={},
                ordenar_por="id",
                ordem="asc"
            )

        except Exception as erro:
            ativos = service.listar_ativos(user_id)
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=f"Erro inesperado ao remover ativo: {erro}",
                usuario_email=session.get("user_email"),
                status_validos=STATUS_VALIDOS,
                filtros={},
                ordenar_por="id",
                ordem="asc"
            )