"""
Extensões partilhadas.

O 'limiter' faz o controlo de quantos pedidos um mesmo endereço IP pode fazer
(proteção contra brute force / spam do lado do servidor). Fica aqui, num ficheiro
próprio, para poder ser importado tanto pela app como pelas rotas sem importações
circulares.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,     # limita por endereço IP
    default_limits=["60 per hour"],  # teto geral por IP
    storage_uri="memory://",         # simples (em memória). Ver nota no README.
)
