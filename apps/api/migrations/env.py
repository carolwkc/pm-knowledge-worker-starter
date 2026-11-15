from alembic import context
from sqlalchemy import create_engine, pool

from pmknowledge.config import Settings
from pmknowledge.models import Base

config = context.config


def run_migrations(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=Settings().database_url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    run_migrations(config.attributes["connection"])
else:
    engine = create_engine(Settings().database_url, poolclass=pool.NullPool, hide_parameters=True)
    with engine.connect() as connection:
        run_migrations(connection)
    engine.dispose()
