# web_app/routes/ativos_routes.py

# Rotas web do módulo de ativos.
# Esta camada deve apenas:
# - receber dados da interface
# - chamar o service
# - renderizar templates
# A regra de negócio permanece no service e nos validators.

from flask import render_template, request, redirect, url_for, session

from services.ativos_service import AtivosService, AtivoErro
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

    @app.route("/ativos")
    def listar_ativos():
        """
        Lista os ativos do usuário autenticado.
        """
        user_id = _obter_user_id_logado()

        if user_id is None:
            return redirect(url_for("login"))

        try:
            ativos = service.listar_ativos(user_id)
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=None,
                usuario_email=session.get("user_email")
            )

        except Exception as erro:
            return render_template(
                "ativos.html",
                ativos=[],
                erro=f"Erro ao listar ativos: {erro}",
                usuario_email=session.get("user_email")
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
            # Lê todos os campos enviados pelo formulário.
            dados = request.form.to_dict()

            try:
                # Monta o objeto Ativo com TODOS os campos do formulário.
                # Aqui estava o problema: nota_fiscal e garantia não estavam sendo repassados.
                ativo = Ativo(
                    id_ativo=dados.get("id", ""),
                    tipo=dados.get("tipo", ""),
                    marca=dados.get("marca", ""),
                    modelo=dados.get("modelo", ""),
                    usuario_responsavel=dados.get("usuario_responsavel", "") or None,
                    departamento=dados.get("departamento", ""),
                    nota_fiscal=dados.get("nota_fiscal", "") or None,
                    # Repassa garantia para o domínio mantendo a regra documental.
                    garantia=dados.get("garantia", "") or None,
                    status=dados.get("status", ""),
                    data_entrada=dados.get("data_entrada", ""),
                    data_saida=dados.get("data_saida", "") or None
                )

                # Envia o objeto ao service para validação e persistência.
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
                # Se o campo vier vazio na web, tratamos como None.
                if "usuario_responsavel" in dados and not dados["usuario_responsavel"].strip():
                    dados["usuario_responsavel"] = None

                # Faz o mesmo tratamento para os novos campos opcionais.
                if "nota_fiscal" in dados and not dados["nota_fiscal"].strip():
                    dados["nota_fiscal"] = None

                # Mantém tratamento de vazio para None também na garantia.
                if "garantia" in dados and not dados["garantia"].strip():
                    dados["garantia"] = None

                if "data_saida" in dados and not dados["data_saida"].strip():
                    dados["data_saida"] = None

                service.atualizar_ativo(
                    id_ativo=id_ativo,
                    dados=dados,
                    user_id=user_id
                )

                return redirect(url_for("listar_ativos"))

            except AtivoErro as erro:
                return render_template(
                    "editar_ativo.html",
                    erro=str(erro),
                    dados=dados,
                    id_ativo=id_ativo,
                    status_validos=STATUS_VALIDOS,
                    usuario_email=session.get("user_email")
                )

            except Exception as erro:
                return render_template(
                    "editar_ativo.html",
                    erro=f"Erro inesperado ao editar ativo: {erro}",
                    dados=dados,
                    id_ativo=id_ativo,
                    status_validos=STATUS_VALIDOS,
                    usuario_email=session.get("user_email")
                )

        try:
            ativo = service.buscar_ativo(id_ativo, user_id)
            dados = ativo.to_dict()

            return render_template(
                "editar_ativo.html",
                erro=None,
                dados=dados,
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
                usuario_email=session.get("user_email")
            )

        except Exception as erro:
            ativos = service.listar_ativos(user_id)
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=f"Erro inesperado ao carregar ativo para edição: {erro}",
                usuario_email=session.get("user_email")
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
                usuario_email=session.get("user_email")
            )

        except Exception as erro:
            ativos = service.listar_ativos(user_id)
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=f"Erro inesperado ao remover ativo: {erro}",
                usuario_email=session.get("user_email")
            )