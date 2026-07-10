"""
Modelo de dados: um Pedido de Orçamento.

Cada coluna corresponde a um campo do formulário de contactos.html.
Os checkboxes ("especial" e "servico") são guardados como texto separado
por vírgulas (ex: "piano, cofre").
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

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
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
