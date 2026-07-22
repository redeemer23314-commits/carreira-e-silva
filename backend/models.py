"""
Modelo de dados: um Pedido de Orçamento.

Cada coluna corresponde a um campo do formulário de contactos.html.
Os checkboxes ("especial" e "servico") são guardados como texto separado
por vírgulas (ex: "piano, cofre").
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from database import Base


class PedidoOrcamento(Base):
    __tablename__ = "pedidos_orcamento"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Dados pessoais
    nome = Column(String(120))
    email = Column(String(120))
    telefone = Column(String(40))
    codigo_postal = Column(String(20))

    # Tipo de mudança
    tipo = Column(String(40))

    # Moradas e acessos
    origem = Column(String(255))
    destino = Column(String(255))
    andar_origem = Column(String(40))
    andar_destino = Column(String(40))
    elevador_origem = Column(String(10))
    elevador_destino = Column(String(10))

    # Itens e serviços
    itens = Column(Text)
    especial = Column(String(255))   # lista separada por vírgulas
    servico = Column(String(255))    # lista separada por vírgulas

    # Datas
    data = Column(String(40))
    flexibilidade = Column(String(60))

    # Mensagem livre
    observacoes = Column(Text)

    # Estado de gestão (marcado pelo admin)
    realizado = Column(Boolean, default=False)

    # Preenchido automaticamente
    criado_em = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Converte o pedido num dicionário (útil para JSON e email)."""
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "telefone": self.telefone,
            "codigo_postal": self.codigo_postal,
            "tipo": self.tipo,
            "origem": self.origem,
            "destino": self.destino,
            "andar_origem": self.andar_origem,
            "andar_destino": self.andar_destino,
            "elevador_origem": self.elevador_origem,
            "elevador_destino": self.elevador_destino,
            "itens": self.itens,
            "especial": self.especial,
            "servico": self.servico,
            "data": self.data,
            "flexibilidade": self.flexibilidade,
            "observacoes": self.observacoes,
            "realizado": bool(self.realizado),
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }


class TentativaLoginFalhada(Base):
    """Registo de uma tentativa de entrar no admin com token errado.

    Usado para duas coisas: mostrar ao admin quem esta a tentar entrar, e
    aplicar o bloqueio de 5 falhas por hora e por IP.
    """

    __tablename__ = "tentativas_login_falhadas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(64), index=True)
    momento = Column(DateTime, default=datetime.utcnow, index=True)
    # O user-agent ajuda a distinguir um browser real de um script.
    user_agent = Column(String(500))

    def to_dict(self):
        return {
            "id": self.id,
            "ip": self.ip,
            "momento": self.momento.isoformat() if self.momento else None,
            "user_agent": self.user_agent,
        }
