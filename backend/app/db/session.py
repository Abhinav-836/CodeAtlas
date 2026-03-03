"""
Database session management with async support (SQLite / PostgreSQL compatible).
"""

import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# -----------------------------
# Configuration
# -----------------------------
DEBUG = True
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./codeatlas.db")
is_sqlite = DATABASE_URL.startswith("sqlite+aiosqlite")

# -----------------------------
# Async Engine
# -----------------------------
async_engine = create_async_engine(
    DATABASE_URL,
    echo=DEBUG,
    future=True,
    poolclass=NullPool if is_sqlite else None,
)

# -----------------------------
# Async Session Factory
# -----------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# -----------------------------
# Sync Session Factory (PostgreSQL only)
# -----------------------------
if not is_sqlite:
    from sqlalchemy import create_engine

    sync_engine = create_engine(
        DATABASE_URL.replace("+asyncpg", ""),
        echo=DEBUG,
        future=True,
    )

    SessionLocal = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
else:
    SessionLocal = None

# -----------------------------
# Async DB Dependency
# -----------------------------
async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# -----------------------------
# Sync DB Dependency
# -----------------------------
def get_db():
    if SessionLocal is None:
        raise RuntimeError("Sync sessions not available for SQLite async")
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# -----------------------------
# DB Utilities
# -----------------------------
async def init_db():
    """Initialize database tables."""
    from app.db.models import Base  # Ensure you have models.py
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

async def close_db():
    """Close database connections."""
    await async_engine.dispose()
    logger.info("Database connections closed")

async def check_db_health() -> dict:
    """Check database connectivity."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute("SELECT 1")
            result.scalar()
            return {"status": "healthy", "database": DATABASE_URL.split('://')[0]}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e), "database": DATABASE_URL.split('://')[0]}
