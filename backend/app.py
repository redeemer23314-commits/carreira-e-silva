"""
Aplicação principal da API da Carreira & Silva.

Para correr localmente:
    cd backend
    python -m venv venv
    venv\\Scripts\\activate        (Windows)   |   source venv/bin/activate  (Linux/Mac)
    pip install -r requirements.txt
    python app.py

A API fica em http://localhost:5000
"""

import os

from flask import Flask, jsonify
from flask_cors import CORS

# Carrega variáveis do ficheiro .env (se existir) em desenvolvimento local.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from database import init_db
from extensions import limiter
from routes.orcamento import bp
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

# O Render (e qualquer alojamento com proxy inverso a frente) passa o IP real
# do visitante no header X-Forwarded-For. Sem isto, request.remote_addr fica
# sempre igual (IP interno do proxy) e o bloqueio por IP do admin nao vale
# nada. O x_for=1 diz "confia num salto de proxy", que e o padrao para Render.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# CORS: quais os sites autorizados a chamar a API.
# Por defeito "*" (qualquer um) para facilitar os testes. Em produção convém
# restringir ao teu site, definindo CORS_ORIGINS no Render, por exemplo:
#   CORS_ORIGINS=https://o-teu-utilizador.github.io
origens = os.environ.get("CORS_ORIGINS", "*")
if origens == "*":
    CORS(app)
else:
    CORS(app, resources={r"/api/*": {"origins": [o.strip() for o in origens.split(",")]}})

# Ativa o rate limiting (proteção contra brute force / spam).
limiter.init_app(app)

# Cria as tabelas se ainda não existirem.
init_db()

# Regista as rotas da API.
app.register_blueprint(bp)


@app.route("/")
def home():
    """Página simples para confirmar que a API está viva."""
    return jsonify({"status": "ok", "servico": "API Carreira & Silva"})


@app.errorhandler(429)
def demasiados_pedidos(erro):
    """Mensagem amigável quando alguém excede o limite de envios."""
    return jsonify({"error": "Demasiados pedidos. Aguarde um momento e tente novamente."}), 429


if __name__ == "__main__":
    app.run(debug=True, port=5000)
