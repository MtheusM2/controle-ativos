# web_app/app.py

from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Sistema de Controle de Ativos"

if __name__ == "__main__":
    app.run(debug=True)