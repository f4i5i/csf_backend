from typing import Any, AsyncGenerator, Dict

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from core.config import config


def get_engine_config(database_url: str) -> Dict[str, Any]:
    """Get database engine configuration based on database type.

    Args:
        database_url: Database connection URL

    Returns:
        Dict of engine configuration parameters
    """
    config_dict = {
        "echo": False,  # Set to True for SQL logging
        "future": True,
    }

    if "postgresql" in database_url:
        # PostgreSQL-specific settings with connection pooling
        config_dict.update({
            "pool_size": config.DATABASE_POOL_SIZE,
            "max_overflow": config.DATABASE_MAX_OVERFLOW,
            "pool_recycle": 3600,  # Recycle connections after 1 hour
            "pool_pre_ping": True,  # Verify connection before use
        })
    elif "sqlite" in database_url:
        # SQLite-specific settings
        config_dict.update({
            "connect_args": {"check_same_thread": False},
            "poolclass": NullPool,  # Disable pooling for SQLite
        })

    return config_dict


# Create async engine with database-specific configuration
engine = create_async_engine(
    config.DATABASE_URL,
    **get_engine_config(config.DATABASE_URL)
)


# Enable foreign key support for SQLite
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints for SQLite databases."""
    if "sqlite" in config.DATABASE_URL:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Create async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async database session.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()