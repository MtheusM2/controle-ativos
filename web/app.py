from flask import Flask, request, jsonify, session

from services.auth_service import (
    AuthService,
    AuthErro,
    UsuarioJaExiste,
    UsuarioNaoEncontrado,
    CredenciaisInvalidas,
    RecuperacaoInvalida
)
from services.ativos_service import (
    AtivosService,
    AtivoErro,
    AtivoJaExiste,
    AtivoNaoEncontrado,
    PermissaoNegada
)
from models.ativos import Ativo

app = Flask(__name__)
app.secret_key = "troque-esta-chave-em-producao"

auth_service = AuthService()
ativos_service = AtivosService()


def usuario_logado_id():
    return session.get("user_id")


@app.post("/register")
def register():
    data = request.get_json()

    try:
        user_id = auth_service.registrar_usuario(
            email=data["email"],
            senha=data["senha"],
            pergunta=data["pergunta_recuperacao"],
            resposta=data["resposta_recuperacao"]
        )
        return jsonify({"ok": True, "user_id": user_id}), 201
    except UsuarioJaExiste as e:
        return jsonify({"ok": False, "erro": str(e)}), 409
    except AuthErro as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.post("/login")
def login():
    data = request.get_json()

    try:
        usuario = auth_service.autenticar(
            email=data["email"],
            senha=data["senha"]
        )
        session["user_id"] = usuario.id
        session["email"] = usuario.email
        return jsonify({"ok": True, "email": usuario.email})
    except (UsuarioNaoEncontrado, CredenciaisInvalidas) as e:
        return jsonify({"ok": False, "erro": str(e)}), 401
    except AuthErro as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.post("/forgot-password")
def forgot_password():
    data = request.get_json()

    try:
        auth_service.redefinir_senha(
            email=data["email"],
            resposta=data["resposta_recuperacao"],
            nova_senha=data["nova_senha"]
        )
        return jsonify({"ok": True})
    except RecuperacaoInvalida as e:
        return jsonify({"ok": False, "erro": str(e)}), 401
    except AuthErro as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.get("/ativos")
def listar_ativos():
    user_id = usuario_logado_id()
    if not user_id:
        return jsonify({"ok": False, "erro": "Não autenticado."}), 401

    ativos = ativos_service.listar_ativos(user_id=user_id)

    return jsonify({
        "ok": True,
        "ativos": [
            {
                "id": a.id_ativo,
                "tipo": a.tipo,
                "marca": a.marca,
                "modelo": a.modelo,
                "usuario": a.usuario,
                "departamento": a.departamento,
                "status": a.status
            }
            for a in ativos
        ]
    })


@app.post("/ativos")
def criar_ativo():
    user_id = usuario_logado_id()
    if not user_id:
        return jsonify({"ok": False, "erro": "Não autenticado."}), 401

    data = request.get_json()

    ativo = Ativo(
        id_ativo=data["id"],
        tipo=data["tipo"],
        marca=data["marca"],
        modelo=data["modelo"],
        usuario=data["usuario"],
        departamento=data["departamento"],
        status=data["status"]
    )

    try:
        ativos_service.criar_ativo(ativo, user_id=user_id)
        return jsonify({"ok": True}), 201
    except AtivoJaExiste as e:
        return jsonify({"ok": False, "erro": str(e)}), 409
    except AtivoErro as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.get("/ativos/<id_ativo>")
def buscar_ativo(id_ativo):
    user_id = usuario_logado_id()
    if not user_id:
        return jsonify({"ok": False, "erro": "Não autenticado."}), 401

    try:
        a = ativos_service.buscar_ativo(id_ativo=id_ativo, user_id=user_id)
        return jsonify({
            "ok": True,
            "ativo": {
                "id": a.id_ativo,
                "tipo": a.tipo,
                "marca": a.marca,
                "modelo": a.modelo,
                "usuario": a.usuario,
                "departamento": a.departamento,
                "status": a.status
            }
        })
    except (AtivoNaoEncontrado, PermissaoNegada) as e:
        return jsonify({"ok": False, "erro": str(e)}), 404
    except AtivoErro as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.put("/ativos/<id_ativo>")
def atualizar_ativo(id_ativo):
    user_id = usuario_logado_id()
    if not user_id:
        return jsonify({"ok": False, "erro": "Não autenticado."}), 401

    data = request.get_json()

    try:
        a = ativos_service.atualizar_ativo(
            id_ativo=id_ativo,
            dados=data,
            user_id=user_id
        )
        return jsonify({
            "ok": True,
            "ativo": {
                "id": a.id_ativo,
                "tipo": a.tipo,
                "marca": a.marca,
                "modelo": a.modelo,
                "usuario": a.usuario,
                "departamento": a.departamento,
                "status": a.status
            }
        })
    except AtivoErro as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.delete("/ativos/<id_ativo>")
def remover_ativo(id_ativo):
    user_id = usuario_logado_id()
    if not user_id:
        return jsonify({"ok": False, "erro": "Não autenticado."}), 401

    try:
        ativos_service.remover_ativo(id_ativo=id_ativo, user_id=user_id)
        return jsonify({"ok": True})
    except AtivoErro as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)