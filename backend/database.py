"""
Configuração da base de dados.

Por defeito usa SQLite (um ficheiro local `orcamentos.db`), que não precisa
de instalar nada. Em produção podes trocar para PostgreSQL definindo a variável
de ambiente DATABASE_URL (o Render oferece um Postgres grátis).
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Se não houver DATABASE_URL definida, usamos um ficheiro SQLite local.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///orcamentos.db")

# Alguns serviços (Render/Heroku) dão o URL como "postgres://", mas as versões
# recentes do SQLAlchemy exigem "postgresql://". Corrigimos automaticamente.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# check_same_thread só é necessário (e só existe) no SQLite.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Fábrica de sessões. Em cada pedido criamos uma sessão nova e fechamo-la no fim.
Session = sessionmaker(bind=engine)

# Classe base de onde os modelos herdam.
Base = declarative_base()


def init_db():
    """Cria as tabelas na base de dados (se ainda não existirem)."""
    # Importa os modelos para que fiquem registados na Base antes de criar.
    import models  # noqa: F401

    Base.metadata.create_all(engine)
    print("[db] Tabelas prontas.")
