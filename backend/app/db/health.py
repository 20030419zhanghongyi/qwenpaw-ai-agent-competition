"""Database liveness probe used by the public health endpoint."""

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .session import engine


def ping_database(database_engine: Engine = engine) -> bool:
    with database_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
