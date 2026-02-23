"""Database engine and session management for KB Architecture.

Uses async SQLAlchemy with asyncpg for PostgreSQL access via Cloud SQL.
Connection string is configured via KB_DATABASE_URL environment variable.
"""

from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DATABASE_URL = os.environ.get(
    "KB_DATABASE_URL",
    "postgresql+asyncpg://kb_admin:changeme@localhost:5432/gpt_panel_kb",
)

# Build engine kwargs based on driver (SQLite doesn't support pool_size/max_overflow)
_engine_kwargs: dict = {"echo": False}
if "sqlite" not in DATABASE_URL:
    _engine_kwargs.update(pool_size=20, max_overflow=40, pool_pre_ping=True)

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session injection."""
    async with async_session_factory() as session:
        yield session
