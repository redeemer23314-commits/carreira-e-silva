# API de Orçamentos — Carreira & Silva

API em Flask que recebe os pedidos de orçamento do formulário do site,
valida e filtra o conteúdo, guarda numa base de dados e envia um email de
notificação à empresa.

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET`  | `/` | Estado da API (verificar se está viva) |
| `POST` | `/api/orcamento` | Recebe um pedido do formulário (máx. 5/min por IP) |
| `GET`  | `/api/orcamentos` | Lista os pedidos — **exige** cabeçalho `X-Admin-Token` |

## Correr localmente (Windows)

```bat
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      REM depois preenche o .env
python app.py
```

A API fica em `http://localhost:5000`.
O site (servido à parte, ex. `python -m http.server 8000`) já a chama automaticamente
quando corre em `localhost`.

## Configuração (ficheiro .env)

Copia `.env.example` para `.env` e preenche. Nunca envies o `.env` para o GitHub.

| Variável | Para quê |
|----------|----------|
| `SMTP_USER` / `SMTP_PASS` | Conta Gmail + **App Password** de 16 caracteres |
| `EMAIL_TO` | Para onde enviar o aviso de cada pedido |
| `ADMIN_TOKEN` | Palavra-passe para consultar `/api/orcamentos` |
| `CORS_ORIGINS` | Sites autorizados (ex. `https://utilizador.github.io`); `*` para testar |
| `DATABASE_URL` | Opcional. Sem isto usa SQLite local |

### Como obter a App Password do Gmail
1. A conta precisa de ter a **verificação em 2 passos** ativada.
2. Ir a **Conta Google → Segurança → Palavras-passe de aplicações**.
3. Gerar uma nova → copiar os 16 caracteres → colar em `SMTP_PASS`.
   (A password normal do Gmail **não** funciona por SMTP.)

## Deploy no Render

1. Põe o projeto no GitHub (a pasta `backend/` incluída).
2. Em [render.com](https://render.com) → **New → Web Service** → liga o repositório.
3. Configura:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
4. Em **Environment**, adiciona as variáveis do `.env` (SMTP_USER, SMTP_PASS,
   EMAIL_TO, ADMIN_TOKEN, CORS_ORIGINS).
5. Deploy. O Render dá um URL tipo `https://a-tua-api.onrender.com`.
6. No site, em `js/orcamento.js`, substitui o URL de produção por esse.

## Notas
- **Cold start:** no plano grátis do Render a API "adormece" após inatividade;
  o primeiro pedido pode demorar ~50s.
- **SQLite no Render (plano grátis):** o disco é efémero — a base de dados pode
  ser apagada em cada redeploy. Para dados persistentes, cria um **PostgreSQL**
  grátis no Render e define `DATABASE_URL`.
- **Rate limit:** guardado em memória. Se um dia usares vários workers, passa a
  usar Redis (`storage_uri`).
