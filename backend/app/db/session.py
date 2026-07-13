"""Synchronous SQLAlchemy engine and session lifecycle."""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def build_engine(database_url: str | None = None) -> Engine:
    return create_engine(
        database_url or settings.database_url,
        echo=settings.db_echo,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


# Engine construction is lazy: no connection or SQL is issued at import time.
engine = build_engine()
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
