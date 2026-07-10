"""
Envio de email de notificacao quando chega um novo pedido de orcamento.
Usa o servico Resend (HTTPS), porque o Render gratis bloqueia SMTP.
"""

import json
import os
import urllib.error
import urllib.request

EMAIL_TESTE = "redeemer23314@gmail.com"
RESEND_URL = "https://api.resend.com/emails"


def enviar_notificacao(pedido: dict) -> bool:
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
    dados = json.dumps(corpo).encode("utf-8")

    requisicao = urllib.request.Request(
        RESEND_URL,
        data=dados,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=15) as resposta:
            resposta.read()
        print(f"[email] Notificacao enviada para {destino}.")
        return True
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", "ignore")
        print(f"[email] Falha ao enviar email (HTTP {erro.code}): {detalhe}")
        return False
    except Exception as erro:
        print("[email] Falha ao enviar email:", erro)
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
