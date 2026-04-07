from __future__ import annotations

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from services.auth_service import (
    AuthErro,
    AuthService,
    CredenciaisInvalidas,
    PermissaoAuthNegada,
    RecuperacaoInvalida,
    UsuarioJaExiste,
    UsuarioNaoEncontrado,
)
from services.empresa_service import EmpresaService
from utils.csrf import validar_token_csrf

REMEMBER_EMAIL_COOKIE = "remember_email"
REMEMBER_ACTIVE_COOKIE = "remember_active"
REMEMBER_COOKIE_MAX_AGE = 60 * 60 * 24 * 180


def _request_data() -> dict:
    """
    Obtem dados do corpo JSON ou de formularios tradicionais.
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


def _is_admin(perfil: str | None) -> bool:
    """
    Centraliza a regra de detecção de perfil administrativo.
    """
    return (perfil or "").strip().lower() in {"adm", "admin"}


def _obter_user_id_logado() -> int | None:
    """
    Retorna o id do usuario logado quando existir sessao valida.
    """
    raw_id = session.get("user_id")
    if raw_id is None:
        return None
    return int(raw_id)


def _json_success(message: str, *, redirect_url: str | None = None, status: int = 200, **payload):
    """
    Padroniza respostas JSON de sucesso da autenticacao.
    """
    body = {"ok": True, "mensagem": message}
    if redirect_url:
        body["redirect_url"] = redirect_url
    body.update(payload)
    response = jsonify(body)
    response.status_code = status
    return response


def _json_error(message: str, status: int = 400, **payload):
    """
    Padroniza respostas JSON de erro da autenticacao.
    """
    body = {"ok": False, "erro": message}
    body.update(payload)
    response = jsonify(body)
    response.status_code = status
    return response


def _montar_contexto_login() -> dict:
    """
    Monta contexto inicial do login usando cookies seguros de preferencia.
    """
    remember_active = request.cookies.get(REMEMBER_ACTIVE_COOKIE) == "1"
    remembered_email = (request.cookies.get(REMEMBER_EMAIL_COOKIE) or "").strip()

    dados = {"email": remembered_email if remember_active else ""}
    return {
        "erro": None,
        "sucesso": None,
        "dados": dados,
        "show_chrome": False,
        "remember_enabled": remember_active,
    }


def _aplicar_cookie_lembrar_me(response, *, ativo: bool, email: str, secure_cookie: bool) -> None:
    """
    Aplica ou remove cookies de preferencia sem armazenar senha em nenhum momento.
    """
    if ativo:
        response.set_cookie(
            REMEMBER_ACTIVE_COOKIE,
            "1",
            max_age=REMEMBER_COOKIE_MAX_AGE,
            httponly=True,
            secure=secure_cookie,
            samesite="Lax",
        )
        response.set_cookie(
            REMEMBER_EMAIL_COOKIE,
            (email or "").strip(),
            max_age=REMEMBER_COOKIE_MAX_AGE,
            httponly=True,
            secure=secure_cookie,
            samesite="Lax",
        )
        return

    response.delete_cookie(REMEMBER_ACTIVE_COOKIE, samesite="Lax")
    response.delete_cookie(REMEMBER_EMAIL_COOKIE, samesite="Lax")


def registrar_rotas_auth(app, *, auth_service: AuthService, empresa_service: EmpresaService):
    """
    Registra a camada HTTP de autenticacao e sessao.
    """

    @app.get("/")
    def home():
        """
        Tela inicial de login.
        """
        if session.get("user_id"):
            return redirect(url_for("dashboard"))

        return render_template("index.html", **_montar_contexto_login())

    @app.get("/login")
    def login_page():
        """
        Mantem rota dedicada para login sem depender de redirect em cadeia.
        """
        if session.get("user_id"):
            return redirect(url_for("dashboard"))

        return render_template("index.html", **_montar_contexto_login())

    @app.post("/login")
    def login():
        """
        Autentica o usuario e devolve a URL de redirecionamento do dashboard.
        """
        dados = _request_data()
        email = dados.get("email", "")
        senha = dados.get("senha", "")
        lembrar_me_solicitado = _parse_bool_flag(dados.get("lembrar_me"))

        try:
            usuario = auth_service.autenticar(email, senha)
            aviso_compatibilidade = None

            # A preferencia persistente pode vir do cadastro anterior ou da marcacao atual.
            lembrar_me_preferido = bool(getattr(usuario, "lembrar_me_ativo", False)) or lembrar_me_solicitado
            if lembrar_me_solicitado and not bool(getattr(usuario, "lembrar_me_ativo", False)):
                try:
                    auth_service.atualizar_preferencia_lembrar_me(int(usuario.id), True)
                except AuthErro as erro:
                    # Mantem login funcional mesmo se a coluna nova ainda nao existir no schema.
                    aviso_compatibilidade = str(erro)

            session.clear()
            session.permanent = lembrar_me_preferido
            session["user_id"] = int(usuario.id)
            session["user_nome"] = getattr(usuario, "nome", None)
            session["user_email"] = usuario.email
            session["user_perfil"] = usuario.perfil
            session["user_empresa_id"] = int(usuario.empresa_id)
            session["user_empresa_nome"] = usuario.empresa_nome

            flash("Login realizado com sucesso.", "success")
            response = _json_success(
                "Login realizado com sucesso.",
                redirect_url=url_for("dashboard"),
                aviso=aviso_compatibilidade,
            )
            _aplicar_cookie_lembrar_me(
                response,
                ativo=lembrar_me_preferido,
                email=usuario.email,
                secure_cookie=bool(app.config.get("SESSION_COOKIE_SECURE", False)),
            )
            return response
        except (UsuarioNaoEncontrado, CredenciaisInvalidas):
            return _json_error("E-mail ou senha inválidos.", status=401)
        except AuthErro as erro:
            return _json_error(str(erro), status=400)

    @app.get("/register")
    def register_page():
        """
        Renderiza a tela de cadastro de usuario.
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
        Mantem compatibilidade com a rota legada de cadastro.
        """
        return redirect(url_for("register_page"))

    @app.post("/register")
    def register():
        """
        Cadastra um novo usuario e orienta o frontend a retornar para a home.
        """
        dados = _request_data()
        email = dados.get("email", "")
        senha = dados.get("senha", "")
        senha_confirmacao = dados.get("senha_confirmacao", "")
        pergunta = dados.get("pergunta", "")
        resposta = dados.get("resposta", "")
        empresa_id = dados.get("empresa_id", "")
        nome = dados.get("nome", "")

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
                nome=nome,
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
        Renderiza a tela de recuperacao de senha.
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
        Mantem compatibilidade com a rota legada de recuperacao.
        """
        return redirect(url_for("recovery_page"))

    @app.post("/forgot-password")
    def forgot_password():
        """
        Busca a pergunta de seguranca ou redefine a senha.
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

    @app.get("/configuracoes")
    def configuracoes_page():
        """
        Exibe preferencias pessoais e administrativas iniciais do usuario logado.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return redirect(url_for("home"))

        try:
            usuario = auth_service.obter_usuario_por_id(user_id)
            session["user_nome"] = usuario.get("nome")
            session["user_email"] = usuario.get("email")
            session["user_perfil"] = usuario.get("perfil")
            session["user_empresa_id"] = usuario.get("empresa_id")
            session["user_empresa_nome"] = usuario.get("empresa_nome")
        except AuthErro as erro:
            flash(str(erro), "danger")
            return redirect(url_for("dashboard"))

        return render_template(
            "configuracoes.html",
            usuario=usuario,
            is_admin=_is_admin(usuario.get("perfil")),
        )

    @app.post("/configuracoes/perfil")
    def atualizar_configuracoes_perfil():
        """
        Atualiza nome do proprio usuario e e-mail somente para perfil admin.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return redirect(url_for("home"))

        # Proteção CSRF: rejeita requisições sem token válido (cross-site form attacks).
        if not validar_token_csrf(request.form.get("csrf_token")):
            flash("Requisição inválida. Tente novamente.", "danger")
            return redirect(url_for("configuracoes_page"))

        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip()

        try:
            usuario = auth_service.atualizar_proprio_perfil(user_id, nome=nome, email=email)
            session["user_nome"] = usuario.get("nome")
            session["user_email"] = usuario.get("email")

            flash("Perfil atualizado com sucesso.", "success")
            response = redirect(url_for("configuracoes_page"))
            if request.cookies.get(REMEMBER_ACTIVE_COOKIE) == "1":
                _aplicar_cookie_lembrar_me(
                    response,
                    ativo=True,
                    email=usuario.get("email") or "",
                    secure_cookie=bool(app.config.get("SESSION_COOKIE_SECURE", False)),
                )
            return response
        except PermissaoAuthNegada as erro:
            flash(str(erro), "danger")
            return redirect(url_for("configuracoes_page"))
        except AuthErro as erro:
            flash(str(erro), "danger")
            return redirect(url_for("configuracoes_page"))

    @app.post("/configuracoes/senha")
    def atualizar_configuracoes_senha():
        """
        Atualiza senha do proprio usuario validando a senha atual.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return redirect(url_for("home"))

        # Proteção CSRF: rejeita requisições sem token válido (cross-site form attacks).
        if not validar_token_csrf(request.form.get("csrf_token")):
            flash("Requisição inválida. Tente novamente.", "danger")
            return redirect(url_for("configuracoes_page"))

        senha_atual = request.form.get("senha_atual", "")
        nova_senha = request.form.get("nova_senha", "")
        confirmar = request.form.get("confirmar_nova_senha", "")

        if nova_senha != confirmar:
            flash("As senhas não coincidem.", "danger")
            return redirect(url_for("configuracoes_page"))

        try:
            auth_service.alterar_senha_propria(user_id, senha_atual=senha_atual, nova_senha=nova_senha)
            flash("Senha atualizada com sucesso.", "success")
        except AuthErro as erro:
            flash(str(erro), "danger")

        return redirect(url_for("configuracoes_page"))

    @app.post("/configuracoes/lembrar-me")
    def atualizar_preferencia_lembrar_me():
        """
        Permite ativar/desativar a persistencia de sessao apenas pela tela de configuracoes.
        """
        user_id = _obter_user_id_logado()
        if user_id is None:
            return redirect(url_for("home"))

        # Proteção CSRF: rejeita requisições sem token válido (cross-site form attacks).
        if not validar_token_csrf(request.form.get("csrf_token")):
            flash("Requisição inválida. Tente novamente.", "danger")
            return redirect(url_for("configuracoes_page"))

        lembrar_me_ativo = _parse_bool_flag(request.form.get("lembrar_me_ativo"))

        try:
            auth_service.atualizar_preferencia_lembrar_me(user_id, lembrar_me_ativo)
            session.permanent = lembrar_me_ativo
            flash("Preferência de login contínuo atualizada.", "success")

            response = redirect(url_for("configuracoes_page"))
            _aplicar_cookie_lembrar_me(
                response,
                ativo=lembrar_me_ativo,
                email=session.get("user_email", ""),
                secure_cookie=bool(app.config.get("SESSION_COOKIE_SECURE", False)),
            )
            return response
        except AuthErro as erro:
            flash(str(erro), "danger")
            return redirect(url_for("configuracoes_page"))

    @app.post("/logout")
    def logout():
        """
        Limpa a sessao e informa o frontend para retornar a tela inicial.
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
        Expoe o contexto minimo da sessao para validacao do frontend.
        """
        if not session.get("user_id"):
            return jsonify({"ok": False, "authenticated": False}), 401

        return jsonify(
            {
                "ok": True,
                "authenticated": True,
                "usuario": {
                    "id": session.get("user_id"),
                    "nome": session.get("user_nome"),
                    "email": session.get("user_email"),
                    "perfil": session.get("user_perfil"),
                    "empresa_id": session.get("user_empresa_id"),
                    "empresa_nome": session.get("user_empresa_nome"),
                },
            }
        )
