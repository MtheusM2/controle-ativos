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
    - inteiro com o ID do usuário
    - None se não houver sessão autenticada
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

        # Se não estiver autenticado, redireciona para login
        if user_id is None:
            return redirect(url_for("login"))

        try:
            # Busca os ativos do usuário autenticado
            ativos = service.listar_ativos(user_id)

            # Converte os objetos de domínio em dicionários para o template
            ativos_dict = [ativo.to_dict() for ativo in ativos]

            # Renderiza a tela de listagem
            return render_template(
                "ativos.html",
                ativos=ativos_dict,
                erro=None,
                usuario_email=session.get("user_email")
            )

        except Exception as erro:
            # Exibe erro genérico de listagem
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
        - GET: exibe o formulário
        - POST: processa o envio do formulário
        """

        # Obtém o usuário autenticado
        user_id = _obter_user_id_logado()

        # Se não estiver autenticado, redireciona para login
        if user_id is None:
            return redirect(url_for("login"))

        # Se o método for POST, processa o cadastro
        if request.method == "POST":
            # Converte os dados enviados em dicionário comum
            dados = request.form.to_dict()

            try:
                # Cria o objeto de domínio a partir do formulário
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

                # Chama o backend para validar e salvar
                service.criar_ativo(ativo, user_id)

                # Redireciona para a listagem após sucesso
                return redirect(url_for("listar_ativos"))

            except AtivoErro as erro:
                # Em caso de erro de negócio, mantém o formulário preenchido
                return render_template(
                    "novo_ativo.html",
                    erro=str(erro),
                    dados=dados,
                    usuario_email=session.get("user_email")
                )

            except Exception as erro:
                # Em caso de erro inesperado, exibe mensagem genérica
                return render_template(
                    "novo_ativo.html",
                    erro=f"Erro inesperado ao cadastrar ativo: {erro}",
                    dados=dados,
                    usuario_email=session.get("user_email")
                )

        # Se o método for GET, apenas exibe o formulário vazio
        return render_template(
            "novo_ativo.html",
            erro=None,
            dados=None,
            usuario_email=session.get("user_email")
        )