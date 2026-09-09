"""Alembic environment.

The database URL comes from the DATABASE_URL environment variable (the same
variable the application uses) rather than from alembic.ini, so migrations run
unchanged against SQLite in development and MySQL in a hosted deployment.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.database import Base, engine as app_engine

# Importing the models registers every table on Base.metadata.
from app import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_engine():
    """Return the engine migrations should run against.

    An explicit ``sqlalchemy.url`` on the Alembic config wins, so a caller can
    target a specific database (the test suite does this). Otherwise the
    application's own engine is used, which reads DATABASE_URL.
    """
    url = config.get_main_option("sqlalchemy.url", None)
    if url:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        return create_engine(url, connect_args=connect_args)
    return app_engine


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to a database."""
    context.configure(
        url=str(get_engine().url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    with get_engine().connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # Required so ALTER TABLE works on SQLite, which cannot alter
            # columns in place and needs the table rebuilt instead.
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
