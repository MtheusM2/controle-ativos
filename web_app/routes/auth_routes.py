# web_app/routes/auth_routes.py

# Rotas web de autenticação.
# Nesta etapa, a sessão passa a carregar:
# - perfil do usuário
# - empresa do usuário
# - nome da empresa
# Isso prepara o sistema para governança e escopo corporativo.

from flask import render_template, request, redirect, url_for, session

from services.auth_service import (
    AuthService,
    AuthErro,
    UsuarioJaExiste,
    UsuarioNaoEncontrado,
    CredenciaisInvalidas,
    RecuperacaoInvalida
)
from services.empresa_service import EmpresaService


def registrar_rotas_auth(app):
    """
    Registra as rotas web relacionadas à autenticação.
    """
    auth_service = AuthService()
    empresa_service = EmpresaService()

    @app.route("/")
    def home():
        """
        Rota inicial do sistema.
        """
        if session.get("user_id"):
            return redirect(url_for("listar_ativos"))

        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """
        Rota responsável pelo login do usuário.
        """
        if session.get("user_id"):
            return redirect(url_for("listar_ativos"))

        if request.method == "POST":
            dados = request.form.to_dict()

            email = dados.get("email", "")
            senha = dados.get("senha", "")

            try:
                usuario = auth_service.autenticar(email, senha)

                session.clear()
                session["user_id"] = int(usuario.id)
                session["user_email"] = usuario.email
                session["user_perfil"] = usuario.perfil
                session["user_empresa_id"] = int(usuario.empresa_id)
                session["user_empresa_nome"] = usuario.empresa_nome

                return redirect(url_for("listar_ativos"))

            except (UsuarioNaoEncontrado, CredenciaisInvalidas, AuthErro) as erro:
                return render_template(
                    "login.html",
                    erro=str(erro),
                    sucesso=None,
                    dados=dados
                )

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
        """
        if session.get("user_id"):
            return redirect(url_for("listar_ativos"))

        empresas = empresa_service.listar_empresas_ativas()

        if request.method == "POST":
            dados = request.form.to_dict()

            email = dados.get("email", "")
            senha = dados.get("senha", "")
            senha_confirmacao = dados.get("senha_confirmacao", "")
            pergunta = dados.get("pergunta", "")
            resposta = dados.get("resposta", "")
            empresa_id = dados.get("empresa_id", "")

            if senha != senha_confirmacao:
                return render_template(
                    "cadastro.html",
                    erro="As senhas não coincidem.",
                    dados=dados,
                    empresas=empresas
                )

            try:
                user_id = auth_service.registrar_usuario(
                    email=email,
                    senha=senha,
                    pergunta=pergunta,
                    resposta=resposta,
                    empresa_id=empresa_id,
                    perfil="usuario"
                )

                # Faz login automático após cadastro.
                # Para isso, autentica novamente e obtém o contexto completo.
                usuario = auth_service.autenticar(email, senha)

                session.clear()
                session["user_id"] = int(user_id)
                session["user_email"] = usuario.email
                session["user_perfil"] = usuario.perfil
                session["user_empresa_id"] = int(usuario.empresa_id)
                session["user_empresa_nome"] = usuario.empresa_nome

                return redirect(url_for("listar_ativos"))

            except (UsuarioJaExiste, AuthErro) as erro:
                return render_template(
                    "cadastro.html",
                    erro=str(erro),
                    dados=dados,
                    empresas=empresas
                )

        return render_template(
            "cadastro.html",
            erro=None,
            dados=None,
            empresas=empresas
        )

    @app.route("/recuperar-senha", methods=["GET", "POST"])
    def recuperar_senha():
        """
        Rota responsável pela recuperação de senha.
        """
        if session.get("user_id"):
            return redirect(url_for("listar_ativos"))

        if request.method == "GET":
            return render_template(
                "recuperar_senha.html",
                erro=None,
                sucesso=None,
                pergunta=None,
                dados=None
            )

        dados = request.form.to_dict()
        acao = dados.get("acao", "buscar_pergunta")
        email = dados.get("email", "")

        if acao == "buscar_pergunta":
            try:
                pergunta = auth_service.obter_pergunta_recuperacao(email)

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

        try:
            pergunta = auth_service.obter_pergunta_recuperacao(email)
        except (UsuarioNaoEncontrado, AuthErro) as erro:
            return render_template(
                "recuperar_senha.html",
                erro=str(erro),
                sucesso=None,
                pergunta=None,
                dados=dados
            )

        resposta = dados.get("resposta", "")
        nova_senha = dados.get("nova_senha", "")
        confirmar_nova_senha = dados.get("confirmar_nova_senha", "")

        if nova_senha != confirmar_nova_senha:
            return render_template(
                "recuperar_senha.html",
                erro="As senhas não coincidem.",
                sucesso=None,
                pergunta=pergunta,
                dados=dados
            )

        try:
            auth_service.redefinir_senha(
                email=email,
                resposta=resposta,
                nova_senha=nova_senha
            )

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
        session.clear()
        return redirect(url_for("login"))