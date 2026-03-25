# Importa request para pegar dados do formulário
from flask import render_template, request, redirect, url_for

from services.ativos_service import AtivosService
from models.ativos import Ativo


def registrar_rotas(app):
    service = AtivosService()

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/ativos")
    def listar_ativos():
        user_id = 1
        ativos = service.listar_ativos(user_id)
        ativos_dict = [ativo.to_dict() for ativo in ativos]
        return render_template("ativos.html", ativos=ativos_dict)

    @app.route("/ativos/novo", methods=["GET", "POST"])
    def criar_ativo():
        """
        Rota para criação de novo ativo via formulário web
        """

        user_id = 1  # TEMPORÁRIO

        if request.method == "POST":
            try:
                # Cria objeto Ativo com dados do formulário
                ativo = Ativo(
                    id_ativo=request.form["id"],
                    tipo=request.form["tipo"],
                    marca=request.form["marca"],
                    modelo=request.form["modelo"],
                    usuario_responsavel=request.form["usuario_responsavel"],
                    departamento=request.form["departamento"],
                    status=request.form["status"],
                    data_entrada=request.form["data_entrada"],
                    data_saida=request.form.get("data_saida")
                )

                # Chama o service
                service.criar_ativo(ativo, user_id)

                # Redireciona para lista
                return redirect(url_for("listar_ativos"))

            except Exception as e:
                return f"Erro: {str(e)}"

        return render_template("novo_ativo.html")