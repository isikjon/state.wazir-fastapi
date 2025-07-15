import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
database_url = os.getenv("DATABASE_URL")

config = context.config
fileConfig(config.config_file_name)

# Импорт моделей для автогенерации миграций
from database import Base
from app.models import *
target_metadata = Base.metadata


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
        url=database_url  # <-- строка подключения из .env
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online() 