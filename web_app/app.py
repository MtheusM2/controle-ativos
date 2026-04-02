
# Arquivo principal da aplicação web.
# Responsável por criar a aplicação Flask,
# definir configurações básicas e registrar rotas.

from pathlib import Path

from flask import Flask

# Importa configuração centralizada para garantir que o .env seja carregado
# antes da configuração do Flask.
from config import FLASK_SECRET_KEY

from web_app.routes.auth_routes import registrar_rotas_auth
from web_app.routes.ativos_routes import registrar_rotas_ativos


# Define a pasta base da aplicação web.
BASE_DIR = Path(__file__).resolve().parent

# Cria a aplicação Flask.
app = Flask(__name__)

# Chave secreta usada pela sessão do Flask.
# Valor vem do módulo central de configuração já validado.
app.config["SECRET_KEY"] = FLASK_SECRET_KEY

# Flags básicas de segurança da sessão.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Configura pasta de uploads.
app.config["UPLOAD_FOLDER"] = str(BASE_DIR / "static" / "uploads")

# Limite máximo de upload: 10 MB.
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# Garante que a pasta física exista.
Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

# Registra as rotas do sistema.
registrar_rotas_auth(app)
registrar_rotas_ativos(app)

if __name__ == "__main__":
    app.run(debug=True)