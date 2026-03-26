# Arquivo responsável pelas rotas web de autenticação:
# - login
# - cadastro
# - recuperação de senha
# - logout

# Importa funções do Flask para:
# - renderizar páginas HTML
# - capturar dados enviados pelo formulário
# - redirecionar o usuário
# - montar URLs com segurança
# - manipular sessão do usuário
from flask import render_template, request, redirect, url_for, session

# Importa o service responsável pelas regras de autenticação
from services.auth_service import (
    AuthService,
    AuthErro,
    UsuarioJaExiste,
    UsuarioNaoEncontrado,
    CredenciaisInvalidas,
    RecuperacaoInvalida
)


def registrar_rotas_auth(app):
    """
    Registra as rotas web relacionadas à autenticação.
    """

    # Instancia o service de autenticação
    auth_service = AuthService()

    @app.route("/")
    def home():
        """
        Rota inicial do sistema.

        Se o usuário já estiver autenticado, redireciona para a listagem de ativos.
        Caso contrário, redireciona para a tela de login.
        """
        if session.get("user_id"):
            return redirect(url_for("listar_ativos"))

        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """
        Rota responsável pelo login do usuário.
        - GET: exibe o formulário
        - POST: autentica o usuário
        """

        # Se o usuário já estiver autenticado, evita novo login desnecessário
        if session.get("user_id"):
            return redirect(url_for("listar_ativos"))

        # Processa envio do formulário
        if request.method == "POST":
            # Converte os dados do formulário em dicionário comum
            dados = request.form.to_dict()

            # Extrai os campos principais
            email = dados.get("email", "")
            senha = dados.get("senha", "")

            try:
                # Autentica o usuário no backend
                usuario = auth_service.autenticar(email, senha)

                # Limpa qualquer sessão anterior
                session.clear()

                # Armazena os dados básicos do usuário autenticado na sessão
                session["user_id"] = int(usuario.id)
                session["user_email"] = usuario.email

                # Redireciona para a tela principal do sistema autenticado
                return redirect(url_for("listar_ativos"))

            except (UsuarioNaoEncontrado, CredenciaisInvalidas, AuthErro) as erro:
                # Em caso de erro, mantém o e-mail preenchido e exibe a mensagem
                return render_template(
                    "login.html",
                    erro=str(erro),
                    sucesso=None,
                    dados=dados
                )

        # Exibe o formulário vazio no primeiro acesso
        return render_template(
            "login.html",
            erro=None,
            sucesso=None,
            dados=None
        )

    @app.route("/cadastro", methods=["GET", "POST"])
    def cadastro_usuario():
        """
        Rota responsável pelo cadastro de um novo usuário.
        - GET: exibe o formulário
        - POST: valida e cadastra o usuário
        """

        # Se já estiver logado, não faz sentido abrir a tela de cadastro
        if session.get("user_id"):
            return redirect(url_for("listar_ativos"))

        # Processa envio do formulário
        if request.method == "POST":
            # Converte os dados do formulário em dicionário comum
            dados = request.form.to_dict()

            # Extrai os campos informados
            email = dados.get("email", "")
            senha = dados.get("senha", "")
            senha_confirmacao = dados.get("senha_confirmacao", "")
            pergunta = dados.get("pergunta", "")
            resposta = dados.get("resposta", "")

            # Valida confirmação de senha antes de chamar o service
            if senha != senha_confirmacao:
                return render_template(
                    "cadastro.html",
                    erro="As senhas não coincidem.",
                    dados=dados
                )

            try:
                # Registra o novo usuário no backend
                user_id = auth_service.registrar_usuario(
                    email=email,
                    senha=senha,
                    pergunta=pergunta,
                    resposta=resposta
                )

                # Faz login automático após o cadastro
                session.clear()
                session["user_id"] = int(user_id)
                session["user_email"] = email.strip().lower()

                # Redireciona para a listagem de ativos
                return redirect(url_for("listar_ativos"))

            except (UsuarioJaExiste, AuthErro) as erro:
                # Em caso de erro, mantém os campos não sensíveis preenchidos
                return render_template(
                    "cadastro.html",
                    erro=str(erro),
                    dados=dados
                )

        # Exibe o formulário vazio no primeiro acesso
        return render_template(
            "cadastro.html",
            erro=None,
            dados=None
        )

    @app.route("/recuperar-senha", methods=["GET", "POST"])
    def recuperar_senha():
        """
        Rota responsável pela recuperação de senha.

        Fluxo:
        1. Usuário informa o e-mail e busca a pergunta
        2. Sistema exibe a pergunta de recuperação
        3. Usuário responde e informa a nova senha
        """

        # Se o usuário já estiver logado, redireciona para a área autenticada
        if session.get("user_id"):
            return redirect(url_for("listar_ativos"))

        # Exibe o formulário vazio
        if request.method == "GET":
            return render_template(
                "recuperar_senha.html",
                erro=None,
                sucesso=None,
                pergunta=None,
                dados=None
            )

        # Converte os dados do formulário em dicionário comum
        dados = request.form.to_dict()

        # Identifica a ação do formulário
        acao = dados.get("acao", "buscar_pergunta")

        # Extrai o e-mail informado
        email = dados.get("email", "")

        # Etapa 1: buscar a pergunta de recuperação
        if acao == "buscar_pergunta":
            try:
                # Busca a pergunta associada ao e-mail
                pergunta = auth_service.obter_pergunta_recuperacao(email)

                # Renderiza a mesma página agora com a pergunta disponível
                return render_template(
                    "recuperar_senha.html",
                    erro=None,
                    sucesso=None,
                    pergunta=pergunta,
                    dados=dados
                )

            except (UsuarioNaoEncontrado, AuthErro) as erro:
                return render_template(
                    "recuperar_senha.html",
                    erro=str(erro),
                    sucesso=None,
                    pergunta=None,
                    dados=dados
                )

        # Etapa 2: validar resposta e redefinir a senha
        try:
            # Busca novamente a pergunta para manter a tela consistente
            pergunta = auth_service.obter_pergunta_recuperacao(email)
        except (UsuarioNaoEncontrado, AuthErro) as erro:
            return render_template(
                "recuperar_senha.html",
                erro=str(erro),
                sucesso=None,
                pergunta=None,
                dados=dados
            )

        # Extrai os campos da redefinição
        resposta = dados.get("resposta", "")
        nova_senha = dados.get("nova_senha", "")
        confirmar_nova_senha = dados.get("confirmar_nova_senha", "")

        # Valida confirmação da nova senha
        if nova_senha != confirmar_nova_senha:
            return render_template(
                "recuperar_senha.html",
                erro="As senhas não coincidem.",
                sucesso=None,
                pergunta=pergunta,
                dados=dados
            )

        try:
            # Chama o backend para redefinir a senha
            auth_service.redefinir_senha(
                email=email,
                resposta=resposta,
                nova_senha=nova_senha
            )

            # Após sucesso, volta para a tela de login com mensagem positiva
            return render_template(
                "login.html",
                erro=None,
                sucesso="Senha redefinida com sucesso. Faça login.",
                dados={"email": email}
            )

        except (RecuperacaoInvalida, UsuarioNaoEncontrado, AuthErro) as erro:
            return render_template(
                "recuperar_senha.html",
                erro=str(erro),
                sucesso=None,
                pergunta=pergunta,
                dados=dados
            )

    @app.route("/logout")
    def logout():
        """
        Rota responsável por encerrar a sessão do usuário.
        """

        # Remove todos os dados da sessão
        session.clear()

        # Redireciona para a tela de login
        return redirect(url_for("login"))