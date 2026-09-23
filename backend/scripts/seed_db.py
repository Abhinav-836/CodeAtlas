"""
Database initialization script.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import async_engine
from app.db.models import Base
from app.core.config import settings


async def init_db() -> None:
    print(f"🔧 Initializing database: {settings.DATABASE_URL}")
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully")
        await create_initial_data()
        print("✅ Database initialization complete")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


async def create_initial_data() -> None:
    print("📝 No initial data required (skipped)")


def main() -> None:
    try:
        asyncio.run(init_db())
    except KeyboardInterrupt:
        print("\n❌ Database initialization cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()