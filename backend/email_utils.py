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
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from html import escape

EMAIL_TESTE = "redeemer23314@gmail.com"
RESEND_URL = "https://api.resend.com/emails"

# Fuso de Portugal continental, para as datas nos emails baterem certo com o
# relogio de quem os le. Nada aqui pode rebentar no arranque: se o zoneinfo ou
# a base de dados de fusos nao existirem, fica UTC -- a hora aparece uma hora
# atrasada no verao, o que e feio mas inofensivo. Uma excecao neste import
# derrubaria a API inteira e o formulario deixaria de aceitar pedidos.
try:
    from zoneinfo import ZoneInfo

    FUSO_LISBOA = ZoneInfo("Europe/Lisbon")
except Exception:
    FUSO_LISBOA = timezone.utc


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
        "subject": f"Novo pedido de orçamento — {pedido.get('nome', 'sem nome')}",
        "html": _corpo_html(pedido),
        # Alternativa em texto, para quem tenha o HTML desligado.
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

    # "alternative" = as duas versoes da mesma mensagem; o cliente de email
    # escolhe. A ordem importa: a preferida vai por ultimo.
    mensagem = MIMEMultipart("alternative")
    mensagem["Subject"] = f"Novo pedido de orçamento — {pedido.get('nome', 'sem nome')}"
    mensagem["From"] = formataddr(("Site Carreira e Silva", remetente))
    mensagem["To"] = destino
    if pedido.get("email"):
        mensagem["Reply-To"] = pedido["email"]
    mensagem.attach(MIMEText(_corpo_email(pedido), "plain", "utf-8"))
    mensagem.attach(MIMEText(_corpo_html(pedido), "html", "utf-8"))

    try:
        if porta == 465:
            servidor = smtplib.SMTP_SSL(host, porta, timeout=10)
        else:
            servidor = smtplib.SMTP(host, porta, timeout=10)
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


def _data_legivel(iso: str) -> str:
    """Converte '2026-07-17T12:07:57.992201' em '17/07/2026 às 13:07'.

    O models.py guarda `criado_em` com datetime.utcnow(), ou seja em UTC e sem
    fuso indicado. O servidor do Render também corre em UTC, por isso o fuso de
    Lisboa tem de ser dito explicitamente -- senao a hora no email fica uma hora
    atrasada no verao face ao relogio de quem o le.
    """
    if not iso:
        return "-"
    try:
        momento = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if momento.tzinfo is None:
            momento = momento.replace(tzinfo=timezone.utc)
        return momento.astimezone(FUSO_LISBOA).strftime("%d/%m/%Y às %H:%M")
    except (ValueError, TypeError):
        return iso


# ---------------------------------------------------------------------------
# Corpo do email em HTML
#
# O Outlook desenha o HTML com o motor do Word: nada de flexbox, grid ou folhas
# de estilo -- so tabelas e CSS em linha. Por isso e que isto parece HTML de
# 2005; e de proposito, e a unica coisa que ele renderiza bem.
#
# Motivo de existir: em texto simples o Outlook "endireita" as mudancas de
# linha ("Removemos quebras de linha adicionais desta mensagem") e cola os
# campos todos num paragrafo. Em HTML as quebras sao explicitas e ele nao lhes
# toca.
# ---------------------------------------------------------------------------

NAVY = "#0B1F3A"
VERMELHO = "#C83232"
CINZA_TEXTO = "#333333"
CINZA_CLARO = "#6B7280"
BORDA = "#E2E5EA"


def _corpo_html(p: dict) -> str:
    def linha_html(rotulo, chave):
        valor = str(p.get(chave) or "").strip() or "—"
        return (
            f'<tr>'
            f'<td style="padding:7px 14px 7px 0;vertical-align:top;color:{CINZA_CLARO};'
            f'font-size:13px;white-space:nowrap;">{escape(rotulo)}</td>'
            f'<td style="padding:7px 0;vertical-align:top;color:{CINZA_TEXTO};'
            f'font-size:14px;">{escape(valor)}</td>'
            f'</tr>'
        )

    def seccao(titulo, linhas):
        corpo = "".join(linhas)
        return (
            f'<tr><td style="padding:26px 28px 0 28px;">'
            f'<div style="font-size:11px;font-weight:bold;letter-spacing:1.2px;'
            f'color:{VERMELHO};text-transform:uppercase;padding-bottom:6px;'
            f'border-bottom:1px solid {BORDA};margin-bottom:10px;">{escape(titulo)}</div>'
            f'<table cellpadding="0" cellspacing="0" border="0" width="100%">{corpo}</table>'
            f'</td></tr>'
        )

    nome = escape(str(p.get("nome") or "Sem nome"))
    email_cliente = str(p.get("email") or "").strip()
    telefone = escape(str(p.get("telefone") or "—"))
    codigo_postal = escape(str(p.get("codigo_postal") or "—"))

    # A mensagem do cliente pode ter varias linhas -- preservamo-las.
    observacoes = str(p.get("observacoes") or "").strip()
    observacoes_html = escape(observacoes).replace("\n", "<br>") if observacoes else "—"

    email_html = (
        f'<a href="mailto:{escape(email_cliente)}" style="color:{NAVY};">{escape(email_cliente)}</a>'
        if email_cliente
        else "—"
    )

    return f"""<!DOCTYPE html>
<html lang="pt">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F4F5F7;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#F4F5F7;padding:24px 12px;">
<tr><td align="center">

<table cellpadding="0" cellspacing="0" border="0" width="600" style="max-width:600px;width:100%;
  background:#ffffff;border:1px solid {BORDA};border-radius:8px;overflow:hidden;
  font-family:'Segoe UI',Arial,Helvetica,sans-serif;">

  <tr><td style="background:{NAVY};padding:18px 28px;">
    <div style="color:#ffffff;font-size:15px;font-weight:bold;letter-spacing:.3px;">
      Novo pedido de orçamento
    </div>
    <div style="color:rgba(255,255,255,.65);font-size:12px;padding-top:2px;">
      Recebido através do site
    </div>
  </td></tr>

  <tr><td style="padding:24px 28px 4px 28px;">
    <div style="font-size:21px;font-weight:bold;color:{NAVY};line-height:1.3;">{nome}</div>
    <table cellpadding="0" cellspacing="0" border="0" style="padding-top:10px;">
      <tr><td style="padding:3px 14px 3px 0;color:{CINZA_CLARO};font-size:13px;">Email</td>
          <td style="padding:3px 0;font-size:14px;">{email_html}</td></tr>
      <tr><td style="padding:3px 14px 3px 0;color:{CINZA_CLARO};font-size:13px;">Telefone</td>
          <td style="padding:3px 0;font-size:14px;color:{CINZA_TEXTO};">{telefone}</td></tr>
      <tr><td style="padding:3px 14px 3px 0;color:{CINZA_CLARO};font-size:13px;">Código postal</td>
          <td style="padding:3px 0;font-size:14px;color:{CINZA_TEXTO};">{codigo_postal}</td></tr>
    </table>
  </td></tr>

  {seccao("Mudança", [
      linha_html("Tipo", "tipo"),
      linha_html("Origem", "origem"),
      linha_html("Destino", "destino"),
      linha_html("Andar (origem)", "andar_origem"),
      linha_html("Andar (destino)", "andar_destino"),
      linha_html("Elevador (origem)", "elevador_origem"),
      linha_html("Elevador (destino)", "elevador_destino"),
  ])}

  {seccao("Itens e serviços", [
      linha_html("Itens a transportar", "itens"),
      linha_html("Itens especiais", "especial"),
      linha_html("Serviços adicionais", "servico"),
  ])}

  {seccao("Datas", [
      linha_html("Data preferencial", "data"),
      linha_html("Flexibilidade", "flexibilidade"),
  ])}

  <tr><td style="padding:26px 28px 0 28px;">
    <div style="font-size:11px;font-weight:bold;letter-spacing:1.2px;color:{VERMELHO};
      text-transform:uppercase;padding-bottom:6px;border-bottom:1px solid {BORDA};
      margin-bottom:10px;">Mensagem</div>
    <div style="font-size:14px;color:{CINZA_TEXTO};line-height:1.65;">{observacoes_html}</div>
  </td></tr>

  <tr><td style="padding:26px 28px 24px 28px;">
    <div style="border-top:1px solid {BORDA};padding-top:14px;font-size:12px;color:{CINZA_CLARO};">
      Recebido em {escape(_data_legivel(p.get("criado_em", "")))} · Responder a este email
      contacta directamente o cliente.
    </div>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def _corpo_email(p: dict) -> str:
    """Versao em texto simples -- alternativa para quem tenha o HTML desligado."""

    def linha(rotulo, chave):
        valor = p.get(chave) or "-"
        return f"{rotulo}: {valor}"

    return "\n".join([
        "Foi recebido um novo pedido de orçamento no site.",
        "",
        "==== DADOS DO CLIENTE ====",
        linha("Nome", "nome"),
        linha("Email", "email"),
        linha("Telefone", "telefone"),
        linha("Código postal", "codigo_postal"),
        "",
        "==== MUDANÇA ====",
        linha("Tipo", "tipo"),
        linha("Morada de origem", "origem"),
        linha("Morada de destino", "destino"),
        linha("Andar (origem)", "andar_origem"),
        linha("Andar (destino)", "andar_destino"),
        linha("Elevador (origem)", "elevador_origem"),
        linha("Elevador (destino)", "elevador_destino"),
        "",
        "==== ITENS E SERVIÇOS ====",
        linha("Itens a transportar", "itens"),
        linha("Itens especiais", "especial"),
        linha("Serviços adicionais", "servico"),
        "",
        "==== DATAS ====",
        linha("Data preferencial", "data"),
        linha("Flexibilidade", "flexibilidade"),
        "",
        "==== MENSAGEM ====",
        p.get("observacoes") or "-",
        "",
        f"(Recebido em {_data_legivel(p.get('criado_em', ''))})",
    ])
