"""
Rotas da API de orçamentos.

  POST /api/orcamento    -> recebe o formulário, valida, filtra, guarda e avisa por email.
  GET  /api/orcamentos   -> lista os pedidos (ADMIN — protegido por token).
"""

import os
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from database import Session
from email_utils import enviar_notificacao
from extensions import limiter
from filtro import limpar_texto, validar_conteudo
from models import PedidoOrcamento, TentativaLoginFalhada

# Politica de bloqueio do admin: 5 falhas na ultima hora bloqueiam esse IP
# durante 1 hora (janela deslizante). Se te bloqueares a ti proprio, espera 1h
# ou reinicia o servico no Render.
MAX_FALHAS = 5
JANELA_MINUTOS = 60

bp = Blueprint("orcamento", __name__)

# Campos que TÊM de vir preenchidos (iguais aos 'required' do formulário).
CAMPOS_OBRIGATORIOS = ["nome", "email", "telefone", "codigo_postal", "tipo", "observacoes"]

# Campos de texto livre onde aplicamos o filtro de conteúdo.
CAMPOS_A_FILTRAR = ["itens", "observacoes", "origem", "destino"]


@bp.route("/api/orcamento", methods=["POST"])
@limiter.limit("5 per minute")  # no máximo 5 envios por minuto por IP
def criar_orcamento():
    dados = request.get_json(silent=True) or {}

    # 1) Campos obrigatórios
    for campo in CAMPOS_OBRIGATORIOS:
        if not str(dados.get(campo, "")).strip():
            return jsonify({"error": f"O campo '{campo}' é obrigatório."}), 400

    # 2) Email minimamente válido
    if "@" not in str(dados.get("email", "")):
        return jsonify({"error": "Email inválido."}), 400

    # 3) Filtro de conteúdo (palavrões, spam, injeção de código)
    ok, motivo = validar_conteudo(*(dados.get(c, "") for c in CAMPOS_A_FILTRAR))
    if not ok:
        return jsonify({"error": motivo}), 400

    # 4) Checkboxes vêm como lista -> guardamos como texto "a, b, c"
    especial = dados.get("especial", "")
    if isinstance(especial, list):
        especial = ", ".join(especial)
    servico = dados.get("servico", "")
    if isinstance(servico, list):
        servico = ", ".join(servico)

    # 5) Criar o pedido (limpar_texto neutraliza HTML/scripts antes de guardar)
    pedido = PedidoOrcamento(
        nome=limpar_texto(dados.get("nome")),
        email=limpar_texto(dados.get("email")),
        telefone=limpar_texto(dados.get("telefone")),
        codigo_postal=limpar_texto(dados.get("codigo_postal")),
        tipo=limpar_texto(dados.get("tipo")),
        origem=limpar_texto(dados.get("origem")),
        destino=limpar_texto(dados.get("destino")),
        andar_origem=limpar_texto(dados.get("andar_origem")),
        andar_destino=limpar_texto(dados.get("andar_destino")),
        elevador_origem=limpar_texto(dados.get("elevador_origem")),
        elevador_destino=limpar_texto(dados.get("elevador_destino")),
        itens=limpar_texto(dados.get("itens")),
        especial=limpar_texto(especial),
        servico=limpar_texto(servico),
        data=limpar_texto(dados.get("data")),
        flexibilidade=limpar_texto(dados.get("flexibilidade")),
        observacoes=limpar_texto(dados.get("observacoes")),
    )

    # 6) Guardar na base de dados
    db = Session()
    try:
        db.add(pedido)
        db.commit()
        pedido_dict = pedido.to_dict()
    except Exception as erro:
        db.rollback()
        print("[db] Erro ao guardar:", erro)
        return jsonify({"error": "Não foi possível guardar o pedido. Tente novamente."}), 500
    finally:
        db.close()

    # 7) Avisar a empresa por email (se falhar, o pedido já esta guardado na mesma).
    #    Blindado: um problema no envio NUNCA pode derrubar o pedido nem dar erro 500.
    try:
        enviar_notificacao(pedido_dict)
    except Exception as erro:
        print("[email] Erro inesperado no envio (ignorado):", erro)

    return jsonify({"mensagem": "Pedido recebido com sucesso! Entraremos em contacto."}), 201


def _ip_do_pedido() -> str:
    """IP de quem esta a fazer o pedido, ja considerando o proxy do Render."""
    # ProxyFix esta ativo no app.py, portanto request.remote_addr ja tem o IP
    # real. Truncamos a 64 chars por seguranca (a coluna e VARCHAR(64)).
    return (request.remote_addr or "desconhecido")[:64]


def _contar_falhas_recentes(db, ip: str) -> int:
    """Quantas falhas este IP teve na janela de bloqueio."""
    limite = datetime.utcnow() - timedelta(minutes=JANELA_MINUTOS)
    return (
        db.query(TentativaLoginFalhada)
        .filter(TentativaLoginFalhada.ip == ip)
        .filter(TentativaLoginFalhada.momento >= limite)
        .count()
    )


def _registar_falha(db, ip: str):
    """Guarda uma tentativa falhada. Erros aqui nunca podem derrubar o pedido."""
    try:
        db.add(
            TentativaLoginFalhada(
                ip=ip,
                user_agent=(request.headers.get("User-Agent", "") or "")[:500],
            )
        )
        db.commit()
    except Exception as erro:
        db.rollback()
        print("[admin] Falha a registar tentativa (ignorado):", erro)


def _verificar_admin():
    """Devolve uma resposta de erro se o token de admin não for válido; senão None.

    Regra de bloqueio: 5 falhas na ultima hora deste IP -> bloqueio ate as
    falhas sairem da janela. Enquanto bloqueado, nem o token certo entra
    (obriga a esperar, mesmo que o atacante acerte -- isto e importante:
    e o que impede um atacante que ande a tentar entrar de destrancar-se
    quando finalmente acerta).

    Quando o token esta correto E o IP nao esta bloqueado, as tentativas
    falhadas anteriores desse IP sao apagadas -- para que uma pessoa que se
    tenha enganado 4 vezes e a quinta acerte nao ande sempre "a beira" do
    bloqueio na proxima vez.
    """
    token_correto = os.environ.get("ADMIN_TOKEN")
    if not token_correto:
        return jsonify({"error": "Área de admin desativada (ADMIN_TOKEN não configurado)."}), 403

    ip = _ip_do_pedido()
    db = Session()
    try:
        # Ja esta bloqueado? Se sim, nem verifica o token.
        if _contar_falhas_recentes(db, ip) >= MAX_FALHAS:
            resposta = jsonify({
                "error": (
                    f"Demasiadas tentativas falhadas. "
                    f"Este endereço está bloqueado durante {JANELA_MINUTOS} minutos."
                ),
                "bloqueado": True,
            })
            return resposta, 429

        # Token correto -> passa e limpa o historico de falhas deste IP.
        if request.headers.get("X-Admin-Token") == token_correto:
            _limpar_falhas(db, ip)
            return None

        # Token errado -> regista falha e recusa.
        _registar_falha(db, ip)
        falhas_agora = _contar_falhas_recentes(db, ip)
        restantes = max(0, MAX_FALHAS - falhas_agora)
        return jsonify({
            "error": "Não autorizado.",
            "falhas": falhas_agora,
            "tentativas_restantes": restantes,
        }), 401
    finally:
        db.close()


def _limpar_falhas(db, ip: str):
    """Apaga o historico de tentativas falhadas deste IP.

    Chamado quando o token correto entra. Se nao havia nada, o DELETE nao faz
    nada e o custo e desprezavel -- por isso corre em todos os pedidos com
    token valido (nao ha forma barata de distinguir "primeiro login" de
    "chamada seguinte").
    """
    try:
        apagadas = (
            db.query(TentativaLoginFalhada)
            .filter(TentativaLoginFalhada.ip == ip)
            .delete(synchronize_session=False)
        )
        if apagadas:
            db.commit()
            print(f"[admin] Login bem-sucedido -- {apagadas} tentativa(s) falhada(s) desse dispositivo apagadas.")
    except Exception as erro:
        db.rollback()
        print("[admin] Falha a limpar tentativas (ignorado):", erro)


@bp.route("/api/orcamentos", methods=["GET"])
def listar_orcamentos():
    """Lista todos os pedidos. Protegido: exige o cabeçalho X-Admin-Token."""
    erro = _verificar_admin()
    if erro:
        return erro

    db = Session()
    try:
        pedidos = db.query(PedidoOrcamento).order_by(PedidoOrcamento.criado_em.desc()).all()
        return jsonify([p.to_dict() for p in pedidos])
    finally:
        db.close()


@bp.route("/api/orcamentos/<int:pedido_id>", methods=["PATCH"])
def atualizar_orcamento(pedido_id):
    """Atualiza o estado de um pedido (ex.: marcar como realizado). Protegido."""
    erro = _verificar_admin()
    if erro:
        return erro

    dados = request.get_json(silent=True) or {}
    db = Session()
    try:
        pedido = db.get(PedidoOrcamento, pedido_id)
        if not pedido:
            return jsonify({"error": "Pedido não encontrado."}), 404
        if "realizado" in dados:
            pedido.realizado = bool(dados["realizado"])
        db.commit()
        return jsonify(pedido.to_dict())
    finally:
        db.close()


@bp.route("/api/orcamentos/<int:pedido_id>", methods=["DELETE"])
def apagar_orcamento(pedido_id):
    """Apaga um pedido definitivamente. Protegido."""
    erro = _verificar_admin()
    if erro:
        return erro

    db = Session()
    try:
        pedido = db.get(PedidoOrcamento, pedido_id)
        if not pedido:
            return jsonify({"error": "Pedido não encontrado."}), 404
        db.delete(pedido)
        db.commit()
        return jsonify({"mensagem": "Pedido apagado."})
    finally:
        db.close()


@bp.route("/api/admin/seguranca", methods=["GET"])
def admin_seguranca():
    """Lista as tentativas falhadas das ultimas 24h e o estado do IP atual."""
    erro = _verificar_admin()
    if erro:
        return erro

    limite = datetime.utcnow() - timedelta(hours=24)
    ip_atual = _ip_do_pedido()

    db = Session()
    try:
        tentativas = (
            db.query(TentativaLoginFalhada)
            .filter(TentativaLoginFalhada.momento >= limite)
            .order_by(TentativaLoginFalhada.momento.desc())
            .limit(200)
            .all()
        )
        return jsonify({
            "politica": {
                "max_falhas": MAX_FALHAS,
                "janela_minutos": JANELA_MINUTOS,
            },
            "ip_atual": ip_atual,
            "falhas_do_ip_atual": _contar_falhas_recentes(db, ip_atual),
            "tentativas": [t.to_dict() for t in tentativas],
            "total_24h": len(tentativas),
        })
    finally:
        db.close()
