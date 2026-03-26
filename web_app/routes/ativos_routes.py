# Arquivo responsável pelas rotas web relacionadas aos ativos

# Importa funções do Flask para:
# - renderizar páginas HTML
# - capturar dados enviados pelo formulário
# - redirecionar o usuário
# - montar URLs com segurança
# - acessar a sessão do usuário autenticado
from flask import render_template, request, redirect, url_for, session

# Importa o service responsável pela regra de negócio dos ativos
from services.ativos_service import AtivosService, AtivoErro

# Importa o model Ativo para criar objetos de domínio
from models.ativos import Ativo


def _obter_user_id_logado() -> int | None:
    """
    Obtém o ID do usuário autenticado a partir da sessão.

    Retorno:
    - inteiro com o ID do usuário autenticado
    - None se não houver usuário logado
    """
    user_id = session.get("user_id")

    if user_id is None:
        return None

    return int(user_id)


def registrar_rotas_ativos(app):
    """
    Registra as rotas web relacionadas aos ativos.
    """

    # Instancia o service de ativos
    service = AtivosService()

    @app.route("/ativos")
    def listar_ativos():
        """
        Rota responsável por listar os ativos do usuário autenticado.
        """

        # Obtém o usuário logado pela sessão
        user_id = _obter_user_id_logado()

        # Se não houver autenticação, redireciona para login
        if user_id is None:
            return redirect(url_for("login"))

        try:
            # Busca os ativos do usuário autenticado
            ativos = service.listar_ativos(user_id)

            # Converte os objetos Ativo em dicionários para facilitar o uso no HTML
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            # Renderiza a tela de listagem
            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=None,
                usuario_email=session.get("user_email")
            )

        except Exception as erro:
            # Em caso de erro inesperado, renderiza a página com mensagem
            return render_template(
                "ativos.html",
                ativos=[],
                erro=f"Erro ao listar ativos: {erro}",
                usuario_email=session.get("user_email")
            )

    @app.route("/ativos/novo", methods=["GET", "POST"])
    def criar_ativo():
        """
        Rota responsável pelo cadastro de um novo ativo.
        - GET: exibe o formulário vazio
        - POST: processa o cadastro
        """

        # Obtém o usuário logado pela sessão
        user_id = _obter_user_id_logado()

        # Se não houver autenticação, redireciona para login
        if user_id is None:
            return redirect(url_for("login"))

        # Se o método for POST, processa os dados enviados
        if request.method == "POST":
            # Converte os dados do formulário em dicionário comum
            dados = request.form.to_dict()

            try:
                # Monta o objeto de domínio a partir dos dados recebidos
                ativo = Ativo(
                    id_ativo=dados.get("id", ""),
                    tipo=dados.get("tipo", ""),
                    marca=dados.get("marca", ""),
                    modelo=dados.get("modelo", ""),
                    usuario_responsavel=dados.get("usuario_responsavel", ""),
                    departamento=dados.get("departamento", ""),
                    status=dados.get("status", ""),
                    data_entrada=dados.get("data_entrada", ""),
                    data_saida=dados.get("data_saida", "")
                )

                # Envia o ativo para o backend realizar validação e persistência
                service.criar_ativo(ativo, user_id)

                # Redireciona para a listagem após sucesso
                return redirect(url_for("listar_ativos"))

            except AtivoErro as erro:
                # Em caso de erro de negócio, mantém os dados preenchidos
                return render_template(
                    "novo_ativo.html",
                    erro=str(erro),
                    dados=dados,
                    usuario_email=session.get("user_email")
                )

            except Exception as erro:
                # Em caso de erro inesperado, informa de forma genérica
                return render_template(
                    "novo_ativo.html",
                    erro=f"Erro inesperado ao cadastrar ativo: {erro}",
                    dados=dados,
                    usuario_email=session.get("user_email")
                )

        # Se o método for GET, exibe o formulário vazio
        return render_template(
            "novo_ativo.html",
            erro=None,
            dados=None,
            usuario_email=session.get("user_email")
        )

    @app.route("/ativos/editar/<id_ativo>", methods=["GET", "POST"])
    def editar_ativo(id_ativo):
        """
        Rota responsável pela edição de um ativo existente.
        - GET: busca o ativo e preenche o formulário
        - POST: processa as alterações
        """

        # Obtém o usuário logado pela sessão
        user_id = _obter_user_id_logado()

        # Se não houver autenticação, redireciona para login
        if user_id is None:
            return redirect(url_for("login"))

        # Se o método for POST, processa as alterações enviadas
        if request.method == "POST":
            # Converte os dados do formulário em dicionário comum
            dados = request.form.to_dict()

            try:
                # Envia os dados para o backend atualizar o ativo
                service.atualizar_ativo(
                    id_ativo=id_ativo,
                    dados=dados,
                    user_id=user_id
                )

                # Após atualizar com sucesso, volta para a listagem
                return redirect(url_for("listar_ativos"))

            except AtivoErro as erro:
                # Em caso de erro de negócio, mantém o formulário preenchido
                return render_template(
                    "editar_ativo.html",
                    erro=str(erro),
                    dados=dados,
                    id_ativo=id_ativo,
                    usuario_email=session.get("user_email")
                )

            except Exception as erro:
                # Em caso de erro inesperado, informa de forma genérica
                return render_template(
                    "editar_ativo.html",
                    erro=f"Erro inesperado ao editar ativo: {erro}",
                    dados=dados,
                    id_ativo=id_ativo,
                    usuario_email=session.get("user_email")
                )

        # Se o método for GET, busca o ativo atual para preencher o formulário
        try:
            # Busca o ativo no backend
            ativo = service.buscar_ativo(id_ativo, user_id)

            # Converte o objeto em dicionário para o template
            dados = ativo.to_dict()

            # Renderiza a tela de edição já preenchida
            return render_template(
                "editar_ativo.html",
                erro=None,
                dados=dados,
                id_ativo=id_ativo,
                usuario_email=session.get("user_email")
            )

        except AtivoErro as erro:
            # Se não conseguir carregar o ativo, volta para a listagem com erro
            ativos = service.listar_ativos(user_id)
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=str(erro),
                usuario_email=session.get("user_email")
            )

        except Exception as erro:
            # Trata erros inesperados ao abrir a tela de edição
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
        Rota responsável por remover um ativo existente.
        O método é POST para evitar remoção acidental por navegação simples.
        """

        # Obtém o usuário logado pela sessão
        user_id = _obter_user_id_logado()

        # Se não houver autenticação, redireciona para login
        if user_id is None:
            return redirect(url_for("login"))

        try:
            # Solicita ao backend a remoção do ativo
            service.remover_ativo(id_ativo, user_id)

            # Redireciona para a listagem após remover com sucesso
            return redirect(url_for("listar_ativos"))

        except AtivoErro as erro:
            # Em caso de erro de negócio, recarrega a listagem com a mensagem
            ativos = service.listar_ativos(user_id)
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=str(erro),
                usuario_email=session.get("user_email")
            )

        except Exception as erro:
            # Em caso de erro inesperado, recarrega a listagem com mensagem genérica
            ativos = service.listar_ativos(user_id)
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=f"Erro inesperado ao remover ativo: {erro}",
                usuario_email=session.get("user_email")
            )