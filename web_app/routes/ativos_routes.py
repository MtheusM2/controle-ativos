# Arquivo responsável pelas rotas relacionadas aos ativos

# Importa renderização de templates HTML
from flask import render_template

# Importa o service de ativos
from services.ativos_service import AtivosService


def registrar_rotas(app):
    """
    Registra as rotas principais da aplicação Flask.
    """

    # Instancia o service (camada de regra de negócio)
    service = AtivosService()

    @app.route("/")
    def home():
        """
        Rota inicial do sistema.
        """
        return render_template("index.html")

    @app.route("/ativos")
    def listar_ativos():
        """
        Rota responsável por listar os ativos do usuário.
        """

        # ⚠️ TEMPORÁRIO: usuário fixo para teste
        user_id = 1

        # Busca os ativos no backend
        ativos = service.listar_ativos(user_id)

        # Converte objetos para dicionário (para facilitar uso no HTML)
        ativos_dict = [ativo.to_dict() for ativo in ativos]

        # Envia os dados para o template
        return render_template("ativos.html", ativos=ativos_dict)