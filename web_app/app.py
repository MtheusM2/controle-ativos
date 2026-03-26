# Arquivo principal da aplicação web
# Responsável por criar a aplicação Flask e registrar as rotas do sistema

# Importa utilitário para leitura de variáveis de ambiente
import os

# Importa a classe principal do Flask
from flask import Flask

# Importa o registrador das rotas de autenticação
from web_app.routes.auth_routes import registrar_rotas_auth

# Importa o registrador das rotas de ativos
from web_app.routes.ativos_routes import registrar_rotas_ativos


# Cria a instância principal da aplicação Flask
app = Flask(__name__)

# Define a chave secreta usada pelo Flask para sessão.
# Em produção, o ideal é mover isso para o arquivo .env.
app.config["SECRET_KEY"] = os.getenv(
    "FLASK_SECRET_KEY",
    "dev-secret-key-controle-ativos"
)

# Define flags básicas de segurança da sessão.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Registra as rotas de autenticação
registrar_rotas_auth(app)

# Registra as rotas de ativos
registrar_rotas_ativos(app)

# Garante que o servidor só será iniciado se este arquivo for executado diretamente
if __name__ == "__main__":
    # Inicia a aplicação em modo de depuração
    app.run(debug=True)