# Arquivo principal da aplicação web
# Responsável por criar a aplicação Flask e registrar as rotas do sistema

# Importa a classe principal do Flask
from flask import Flask

# Importa a função responsável por registrar as rotas
from web_app.routes.ativos_routes import registrar_rotas

# Cria a instância principal da aplicação Flask
app = Flask(__name__)

# Registra todas as rotas do sistema
registrar_rotas(app)

# Garante que o servidor só será iniciado se este arquivo for executado diretamente
if __name__ == "__main__":
    # Inicia a aplicação em modo de depuração
    app.run(debug=True)