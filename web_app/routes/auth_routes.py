from __future__ import annotations

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from services.auth_service import (
    AuthErro,
    AuthService,
    CredenciaisInvalidas,
    RecuperacaoInvalida,
    UsuarioJaExiste,
    UsuarioNaoEncontrado,
)
from services.empresa_service import EmpresaService


def _request_data() -> dict:
    """
    Obtém dados do corpo JSON ou de formulários tradicionais.
    """
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def _parse_bool_flag(raw_value) -> bool:
    """
    Normaliza flags booleanas vindas de checkbox/form/json.
    """
    value = str(raw_value or "").strip().lower()
    return value in {"1", "true", "on", "yes", "sim"}


def _json_success(message: str, *, redirect_url: str | None = None, status: int = 200, **payload):
    """
    Padroniza respostas JSON de sucesso da autenticação.
    """
    body = {"ok": True, "mensagem": message}
    if redirect_url:
        body["redirect_url"] = redirect_url
    body.update(payload)
    return jsonify(body), status


def _json_error(message: str, status: int = 400, **payload):
    """
    Padroniza respostas JSON de erro da autenticação.
    """
    body = {"ok": False, "erro": message}
    body.update(payload)
    return jsonify(body), status


def registrar_rotas_auth(app, *, auth_service: AuthService, empresa_service: EmpresaService):
    """
    Registra a camada HTTP de autenticação e sessão.
    """

    @app.get("/")
    def home():
        """
        Tela inicial de login.
        """
        if session.get("user_id"):
            return redirect(url_for("dashboard"))

        return render_template("index.html", erro=None, sucesso=None, dados=None, show_chrome=False)

    @app.get("/login")
    def login_page():
        """
        Mantem rota dedicada para login sem depender de redirect em cadeia.
        """
        if session.get("user_id"):
            return redirect(url_for("dashboard"))

        return render_template("index.html", erro=None, sucesso=None, dados=None, show_chrome=False)

    @app.post("/login")
    def login():
        """
        Autentica o usuário e devolve a URL de redirecionamento do dashboard.
        """
        dados = _request_data()
        email = dados.get("email", "")
        senha = dados.get("senha", "")
        lembrar_me = _parse_bool_flag(dados.get("lembrar_me"))

        try:
            usuario = auth_service.autenticar(email, senha)
            session.clear()
            # Quando habilitado, usa cookie permanente com TTL da configuracao central.
            session.permanent = lembrar_me
            session["user_id"] = int(usuario.id)
            session["user_email"] = usuario.email
            session["user_perfil"] = usuario.perfil
            session["user_empresa_id"] = int(usuario.empresa_id)
            session["user_empresa_nome"] = usuario.empresa_nome
            flash("Login realizado com sucesso.", "success")
            return _json_success("Login realizado com sucesso.", redirect_url=url_for("dashboard"))
        except (UsuarioNaoEncontrado, CredenciaisInvalidas):
            return _json_error("E-mail ou senha inválidos.", status=401)
        except AuthErro as erro:
            return _json_error(str(erro), status=400)

    @app.get("/register")
    def register_page():
        """
        Renderiza a tela de cadastro de usuário.
        """
        if session.get("user_id"):
            return redirect(url_for("dashboard"))

        empresas = empresa_service.listar_empresas_ativas()
        return render_template(
            "register.html",
            erro=None,
            sucesso=None,
            dados=None,
            empresas=empresas,
            show_chrome=False,
        )

    @app.get("/cadastro")
    def cadastro_usuario():
        """
        Mantém compatibilidade com a rota legada de cadastro.
        """
        return redirect(url_for("register_page"))

    @app.post("/register")
    def register():
        """
        Cadastra um novo usuário e orienta o frontend a retornar para a home.
        """
        dados = _request_data()
        email = dados.get("email", "")
        senha = dados.get("senha", "")
        senha_confirmacao = dados.get("senha_confirmacao", "")
        pergunta = dados.get("pergunta", "")
        resposta = dados.get("resposta", "")
        empresa_id = dados.get("empresa_id", "")

        if senha != senha_confirmacao:
            return _json_error("As senhas não coincidem.", status=400)

        try:
            auth_service.registrar_usuario(
                email=email,
                senha=senha,
                pergunta=pergunta,
                resposta=resposta,
                empresa_id=empresa_id,
                perfil="usuario",
            )
            flash("Usuário cadastrado com sucesso. Faça login.", "success")
            return _json_success("Usuário cadastrado com sucesso.", redirect_url=url_for("home"), status=201)
        except UsuarioJaExiste as erro:
            return _json_error(str(erro), status=409)
        except AuthErro as erro:
            return _json_error(str(erro), status=400)

    @app.get("/recovery")
    def recovery_page():
        """
        Renderiza a tela de recuperação de senha.
        """
        if session.get("user_id"):
            return redirect(url_for("dashboard"))

        return render_template(
            "recovery.html",
            erro=None,
            sucesso=None,
            pergunta=None,
            dados=None,
            show_chrome=False,
        )

    @app.get("/recuperar-senha")
    def recuperar_senha():
        """
        Mantém compatibilidade com a rota legada de recuperação.
        """
        return redirect(url_for("recovery_page"))

    @app.post("/forgot-password")
    def forgot_password():
        """
        Busca a pergunta de segurança ou redefine a senha.
        """
        dados = _request_data()
        acao = dados.get("acao", "buscar_pergunta")
        email = dados.get("email", "")

        if acao == "buscar_pergunta":
            try:
                pergunta = auth_service.obter_pergunta_recuperacao(email)
                return _json_success(
                    "Pergunta de recuperação localizada.",
                    pergunta=pergunta,
                    email=email,
                )
            except (UsuarioNaoEncontrado, AuthErro) as erro:
                return _json_error(str(erro), status=404)

        resposta = dados.get("resposta", "")
        nova_senha = dados.get("nova_senha", "")
        confirmar_nova_senha = dados.get("confirmar_nova_senha", "")

        if nova_senha != confirmar_nova_senha:
            return _json_error("As senhas não coincidem.", status=400)

        try:
            auth_service.redefinir_senha(email=email, resposta=resposta, nova_senha=nova_senha)
            flash("Senha redefinida com sucesso. Faça login.", "success")
            return _json_success("Senha redefinida com sucesso.", redirect_url=url_for("home"))
        except RecuperacaoInvalida as erro:
            return _json_error(str(erro), status=401)
        except (UsuarioNaoEncontrado, AuthErro) as erro:
            return _json_error(str(erro), status=400)

    @app.post("/logout")
    def logout():
        """
        Limpa a sessão e informa o frontend para retornar à tela inicial.
        """
        session.clear()
        flash("Logout realizado com sucesso.", "info")
        return _json_success("Logout realizado com sucesso.", redirect_url=url_for("home"))

    @app.get("/logout")
    def logout_web():
        """
        Mantem compatibilidade da navegacao web por link direto de logout.
        """
        session.clear()
        flash("Logout realizado com sucesso.", "info")
        return redirect(url_for("home"))

    @app.get("/session")
    def current_session():
        """
        Expõe o contexto mínimo da sessão para validação do frontend.
        """
        if not session.get("user_id"):
            return jsonify({"ok": False, "authenticated": False}), 401

        return jsonify(
            {
                "ok": True,
                "authenticated": True,
                "usuario": {
                    "id": session.get("user_id"),
                    "email": session.get("user_email"),
                    "perfil": session.get("user_perfil"),
                    "empresa_id": session.get("user_empresa_id"),
                    "empresa_nome": session.get("user_empresa_nome"),
                },
            }
        )
