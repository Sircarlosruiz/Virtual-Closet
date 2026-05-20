import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import pool

from core.config import settings
from core.database import engine

# this is the Alembic Config object
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from models import Base  # noqa: E402, F401

target_metadata = Base.metadata


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async engine."""

    def do_migrations(connection):
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

    if isinstance(engine, AsyncEngine):
        async with engine.begin() as conn:
            await conn.run_sync(do_migrations)
    else:
        raise RuntimeError("Expected async engine")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
