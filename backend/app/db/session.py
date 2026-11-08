"""
Database session management with async support (SQLite / PostgreSQL compatible).
"""

import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ── Configuration ──────────────────────────────────────────────────
DATABASE_URL = settings.database_url  # normalizes sqlite -> sqlite+aiosqlite
is_sqlite = DATABASE_URL.startswith("sqlite+aiosqlite")

# ── Check the URL first, with an error that says what to fix ───────
try:
    _parsed = make_url(DATABASE_URL)
except ArgumentError:
    raise RuntimeError(
        "DATABASE_URL isn't a valid database connection string. It should look like "
        "postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require (for Neon: Dashboard → Connect → "
        "copy the connection string, not the psql command). Check the value in your host's "
        "environment settings."
    ) from None
if not _parsed.drivername.startswith(("sqlite", "postgresql")):
    raise RuntimeError(
        f"DATABASE_URL uses an unsupported database ({_parsed.drivername}). Use PostgreSQL or SQLite."
    )

# ── Async Engine ───────────────────────────────────────────────────
async_engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    poolclass=NullPool if is_sqlite else None,
    pool_pre_ping=not is_sqlite,
    # Neon's pooled endpoint is PgBouncer, which can't keep prepared statements.
    connect_args={} if is_sqlite else {"prepare_threshold": None},
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# ── Sync Session Factory (PostgreSQL only) ─────────────────────────
if not is_sqlite:
    sync_engine = create_engine(
        DATABASE_URL,  # postgresql+psycopg works synchronously too
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )
    SessionLocal = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
else:
    SessionLocal = None


# ── Dependencies ───────────────────────────────────────────────────
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


# ── DB Utilities ───────────────────────────────────────────────────
async def init_db() -> None:
    from app.db.models import Base
    import app.services.report_store  # noqa: F401  (registers the stored_reports table)

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


async def close_db() -> None:
    await async_engine.dispose()
    logger.info("Database connections closed")


async def check_db_health() -> dict:
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            return {"status": "healthy", "database": DATABASE_URL.split("://")[0]}  # never the URL: it has the password
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": DATABASE_URL.split("://")[0],
        }