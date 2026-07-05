"""Alembic migration environment.

The database URL comes from application settings (never hard-coded here), and
``target_metadata`` is the ORM metadata so ``--autogenerate`` sees every table.
Batch mode is enabled for SQLite so column/constraint alterations work.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context

from real_estate.infrastructure.config.settings import Settings
from real_estate.infrastructure.persistence.database import create_db_engine
from real_estate.infrastructure.persistence.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_database_url = Settings(_env_file=None).database_url


def run_migrations_offline() -> None:
    """Emit SQL to a script without a live DB connection."""
    context.configure(
        url=_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    engine = create_db_engine(_database_url)
    with engine.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
