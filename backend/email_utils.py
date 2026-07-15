"""
Envio de email de notificacao quando chega um novo pedido de orcamento.

Suporta dois metodos, escolhidos pela variavel de ambiente EMAIL_METODO:
  - "resend" (por defeito) -> envia via API Resend (HTTPS). Util no Render
    gratis, que bloqueia SMTP.
  - "smtp" -> envia pelo servidor de email do proprio dominio (ex.: no
    alojamento da Createinfor, usando a conta geral@carreiraesilva.pt).

Assim, o mesmo codigo funciona no Render (Resend) e, quando o backend passar
para o alojamento proprio, basta por EMAIL_METODO=smtp.
"""

import os
import json
import smtplib
import urllib.error
import urllib.request
from email.mime.text import MIMEText
from email.utils import formataddr

EMAIL_TESTE = "redeemer23314@gmail.com"
RESEND_URL = "https://api.resend.com/emails"


def enviar_notificacao(pedido: dict) -> bool:
    """Envia a notificacao pelo metodo configurado (resend ou smtp)."""
    metodo = os.environ.get("EMAIL_METODO", "resend").strip().lower()
    if metodo == "smtp":
        return _enviar_smtp(pedido)
    return _enviar_resend(pedido)


# ---------------------------------------------------------------------------
# Metodo 1: Resend (API HTTPS)
# ---------------------------------------------------------------------------
def _enviar_resend(pedido: dict) -> bool:
    api_key = os.environ.get("RESEND_API_KEY")
    destino = os.environ.get("EMAIL_TO", EMAIL_TESTE)
    remetente = os.environ.get("RESEND_FROM", "onboarding@resend.dev")

    if not api_key:
        print("[email] RESEND_API_KEY nao configurada -- envio de email saltado.")
        return False

    corpo = {
        "from": f"Site Carreira e Silva <{remetente}>",
        "to": [destino],
        "subject": f"Novo pedido de orcamento -- {pedido.get('nome', 'sem nome')}",
        "text": _corpo_email(pedido),
    }
    # Responder ao email vai direto para o cliente.
    if pedido.get("email"):
        corpo["reply_to"] = pedido["email"]

    dados = json.dumps(corpo).encode("utf-8")

    requisicao = urllib.request.Request(
        RESEND_URL,
        data=dados,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=15) as resposta:
            resposta.read()
        print(f"[email] Notificacao enviada (Resend) para {destino}.")
        return True
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", "ignore")
        print(f"[email] Falha ao enviar email (HTTP {erro.code}): {detalhe}")
        return False
    except Exception as erro:
        print("[email] Falha ao enviar email (Resend):", erro)
        return False


# ---------------------------------------------------------------------------
# Metodo 2: SMTP (servidor de email do proprio dominio)
# ---------------------------------------------------------------------------
def _enviar_smtp(pedido: dict) -> bool:
    host = os.environ.get("SMTP_HOST")
    porta = int(os.environ.get("SMTP_PORT", "587"))
    utilizador = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    destino = os.environ.get("EMAIL_TO", EMAIL_TESTE)
    remetente = os.environ.get("SMTP_FROM", utilizador)

    if not (host and utilizador and password):
        print("[email] Configuracao SMTP incompleta (SMTP_HOST/USER/PASS) -- envio saltado.")
        return False

    mensagem = MIMEText(_corpo_email(pedido), "plain", "utf-8")
    mensagem["Subject"] = f"Novo pedido de orcamento -- {pedido.get('nome', 'sem nome')}"
    mensagem["From"] = formataddr(("Site Carreira e Silva", remetente))
    mensagem["To"] = destino
    if pedido.get("email"):
        mensagem["Reply-To"] = pedido["email"]

    try:
        if porta == 465:
            servidor = smtplib.SMTP_SSL(host, porta, timeout=20)
        else:
            servidor = smtplib.SMTP(host, porta, timeout=20)
            servidor.ehlo()
            servidor.starttls()
        with servidor:
            servidor.login(utilizador, password)
            servidor.sendmail(remetente, [destino], mensagem.as_string())
        print(f"[email] Notificacao enviada (SMTP) para {destino}.")
        return True
    except Exception as erro:
        print("[email] Falha ao enviar email (SMTP):", erro)
        return False


def _corpo_email(p: dict) -> str:
    def linha(rotulo, chave):
        valor = p.get(chave) or "-"
        return f"{rotulo}: {valor}"

    return "\n".join([
        "Foi recebido um novo pedido de orcamento no site.",
        "",
        "==== DADOS DO CLIENTE ====",
        linha("Nome", "nome"),
        linha("Email", "email"),
        linha("Telefone", "telefone"),
        linha("Codigo postal", "codigo_postal"),
        "",
        "==== MUDANCA ====",
        linha("Tipo", "tipo"),
        linha("Morada de origem", "origem"),
        linha("Morada de destino", "destino"),
        linha("Andar (origem)", "andar_origem"),
        linha("Andar (destino)", "andar_destino"),
        linha("Elevador (origem)", "elevador_origem"),
        linha("Elevador (destino)", "elevador_destino"),
        "",
        "==== ITENS E SERVICOS ====",
        linha("Itens a transportar", "itens"),
        linha("Itens especiais", "especial"),
        linha("Servicos adicionais", "servico"),
        "",
        "==== DATAS ====",
        linha("Data preferencial", "data"),
        linha("Flexibilidade", "flexibilidade"),
        "",
        "==== MENSAGEM ====",
        p.get("observacoes") or "-",
        "",
        f"(Recebido em {p.get('criado_em', '')})",
    ])
