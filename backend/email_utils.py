"""
Envio de email de notificação quando chega um novo pedido de orçamento.

As credenciais NUNCA são escritas no código — vêm de variáveis de ambiente
(ficheiro .env em local, ou painel do Render em produção):

    SMTP_HOST   (por defeito smtp.gmail.com)
    SMTP_PORT   (por defeito 587)
    SMTP_USER   -> a tua conta Gmail (ex: redeemer23314@gmail.com)
    SMTP_PASS   -> a "App Password" de 16 caracteres do Gmail (NÃO a password normal)
    EMAIL_TO    -> para onde enviar o aviso (por defeito o teu email de teste)

Se SMTP_USER/SMTP_PASS não estiverem definidos, o envio é simplesmente saltado
(o pedido continua a ser guardado na base de dados na mesma).
"""

import os
import smtplib
import ssl
from email.message import EmailMessage

import socket


# --- Forçar IPv4 (fix Render: "[Errno 101] Network is unreachable") ---
_getaddrinfo_original = socket.getaddrinfo


def _apenas_ipv4(*args, **kwargs):
    respostas = _getaddrinfo_original(*args, **kwargs)
    ipv4 = [r for r in respostas if r[0] == socket.AF_INET]
    return ipv4 or respostas


socket.getaddrinfo = _apenas_ipv4

# Email de teste pedido pelo utilizador (mudar depois para o email da empresa).
EMAIL_TESTE = "redeemer23314@gmail.com"


def enviar_notificacao(pedido: dict) -> bool:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    destino = os.environ.get("EMAIL_TO", EMAIL_TESTE)

    if not user or not password:
        print("[email] SMTP_USER/SMTP_PASS não configurados — envio de email saltado.")
        return False

    msg = EmailMessage()
    msg["Subject"] = f"Novo pedido de orçamento — {pedido.get('nome', 'sem nome')}"
    msg["From"] = user
    msg["To"] = destino
    msg.set_content(_corpo_email(pedido))

    try:
        contexto = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=15) as servidor:
            servidor.starttls(context=contexto)
            servidor.login(user, password)
            servidor.send_message(msg)
        print(f"[email] Notificação enviada para {destino}.")
        return True
    except Exception as erro:
        # Nunca deixamos o email rebentar o pedido: registamos e seguimos.
        print("[email] Falha ao enviar email:", erro)
        return False


def _corpo_email(p: dict) -> str:
    """Monta o texto do email de forma legível."""
    def linha(rotulo, chave):
        valor = p.get(chave) or "—"
        return f"{rotulo}: {valor}"

    return "\n".join([
        "Foi recebido um novo pedido de orçamento no site.",
        "",
        "── DADOS DO CLIENTE ─────────────────────────",
        linha("Nome", "nome"),
        linha("Email", "email"),
        linha("Telefone", "telefone"),
        linha("Código postal", "codigo_postal"),
        "",
        "── MUDANÇA ──────────────────────────────────",
        linha("Tipo", "tipo"),
        linha("Morada de origem", "origem"),
        linha("Morada de destino", "destino"),
        linha("Andar (origem)", "andar_origem"),
        linha("Andar (destino)", "andar_destino"),
        linha("Elevador (origem)", "elevador_origem"),
        linha("Elevador (destino)", "elevador_destino"),
        "",
        "── ITENS E SERVIÇOS ─────────────────────────",
        linha("Itens a transportar", "itens"),
        linha("Itens especiais", "especial"),
        linha("Serviços adicionais", "servico"),
        "",
        "── DATAS ─────────────────────────────────────",
        linha("Data preferencial", "data"),
        linha("Flexibilidade", "flexibilidade"),
        "",
        "── MENSAGEM ──────────────────────────────────",
        p.get("observacoes") or "—",
        "",
        f"(Recebido em {p.get('criado_em', '')})",
    ])
