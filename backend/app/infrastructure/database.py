"""SQLAlchemy database lifecycle and schema base."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, url: str) -> None:
        self._prepare_sqlite_directory(url)
        is_memory_sqlite = (
            url.startswith("sqlite")
            and url.rsplit("/", maxsplit=1)[-1] == ":memory:"
        )
        connect_args = (
            {"check_same_thread": False}
            if url.startswith("sqlite")
            else {}
        )
        engine_options = (
            {"poolclass": StaticPool}
            if is_memory_sqlite
            else {}
        )
        self.engine: Engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args=connect_args,
            **engine_options,
        )
        self.sessions: sessionmaker[Session] = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def dispose(self) -> None:
        self.engine.dispose()

    @staticmethod
    def _prepare_sqlite_directory(url: str) -> None:
        prefix = "sqlite+pysqlite:///"
        if not url.startswith(prefix):
            return
        raw_path = url.removeprefix(prefix)
        if raw_path == ":memory:":
            return
        Path(raw_path).expanduser().resolve().parent.mkdir(
            parents=True,
            exist_ok=True,
        )
