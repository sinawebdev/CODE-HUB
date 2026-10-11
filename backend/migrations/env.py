"""Alembic environment: the database URL comes from app settings (.env), models from every module."""
from logging.config import fileConfig

from alembic import context

from app.core.config import settings
from app.core.database import Base, UTCDateTime
from app.core.database_connection import make_database_engine, parse_database_url
from app.modules import load_models

config = context.config
migration_url = settings.migration_database_url or settings.database_url
config.set_main_option("sqlalchemy.url", parse_database_url(migration_url).render_as_string(hide_password=False).replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

load_models()
target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """Write our UTCDateTime columns as plain timezone-aware DateTime in migration files."""
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = make_database_engine(migration_url, migration=True)
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, render_item=render_item, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

