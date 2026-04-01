
# Arquivo principal da aplicação web.
# Responsável por criar a aplicação Flask,
# definir configurações básicas e registrar rotas.

import os
from pathlib import Path

from flask import Flask

from web_app.routes.auth_routes import registrar_rotas_auth
from web_app.routes.ativos_routes import registrar_rotas_ativos


# Define a pasta base da aplicação web.
BASE_DIR = Path(__file__).resolve().parent

# Cria a aplicação Flask.
app = Flask(__name__)

# Chave secreta usada pela sessão do Flask.
app.config["SECRET_KEY"] = os.getenv(
    "FLASK_SECRET_KEY",
    "dev-secret-key-controle-ativos"
)

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