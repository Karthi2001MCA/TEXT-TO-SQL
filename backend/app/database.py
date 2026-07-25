"""
Database module - SQLAlchemy async setup.
Manages two databases:
  1. App DB - Users, metadata, audit logs
  2. Data DB - User-uploaded data tables
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, inspect, MetaData
import os
from .config import get_settings


settings = get_settings()

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# ============================================
# App Database (users, metadata, logs)
# ============================================
app_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

AppSessionLocal = async_sessionmaker(
    app_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ============================================
# Data Database (user-uploaded tables)
# ============================================
data_engine = create_async_engine(
    settings.DATA_DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

DataSessionLocal = async_sessionmaker(
    data_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def init_app_db():
    """Create all app database tables."""
    async with app_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def init_data_db():
    """Initialize the data database."""
    # Data DB tables are created dynamically when users upload Excel files
    pass


async def get_app_db() -> AsyncSession:
    """Dependency: get app database session."""
    async with AppSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_data_db() -> AsyncSession:
    """Dependency: get data database session."""
    async with DataSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def execute_raw_sql(query: str, db_session: AsyncSession = None):
    """Execute a raw SQL query on the data database."""
    if db_session:
        result = await db_session.execute(text(query))
        return result
    else:
        async with DataSessionLocal() as session:
            result = await session.execute(text(query))
            return result


async def get_data_db_tables() -> list:
    """Get list of all tables in the data database."""
    async with data_engine.connect() as conn:
        def _get_tables(sync_conn):
            inspector = inspect(sync_conn)
            return inspector.get_table_names()
        tables = await conn.run_sync(_get_tables)
        return tables


async def get_table_columns(table_name: str) -> list:
    """Get columns for a specific table in data database."""
    async with data_engine.connect() as conn:
        def _get_columns(sync_conn):
            inspector = inspect(sync_conn)
            return inspector.get_columns(table_name)
        columns = await conn.run_sync(_get_columns)
        return columns


async def get_table_row_count(table_name: str) -> int:
    """Get row count for a table."""
    async with DataSessionLocal() as session:
        result = await session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
        count = result.scalar()
        return count


async def get_table_sample(table_name: str, limit: int = 10) -> dict:
    """Get sample rows from a table."""
    async with DataSessionLocal() as session:
        result = await session.execute(
            text(f'SELECT * FROM "{table_name}" LIMIT :limit'),
            {"limit": limit}
        )
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return {"columns": columns, "rows": rows, "total": len(rows)}
