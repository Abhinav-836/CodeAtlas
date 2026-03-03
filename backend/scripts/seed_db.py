"""
Database initialization script.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import engine
from app.db.models import Base
from app.core.config import settings


async def init_db():
    """Initialize database."""
    print(f"🔧 Initializing database: {settings.DATABASE_URL}")
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database tables created successfully")
        
        # Optional: Create initial data
        await create_initial_data()
        
        print("✅ Database initialization complete")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


async def create_initial_data():
    """Create initial data if needed."""
    from app.db.session import AsyncSessionLocal
    from app.db import crud
    
    # Example: Create default admin user if using auth
    # async with AsyncSessionLocal() as session:
    #     user_count = await crud.count_users(session)
    #     if user_count == 0:
    #         admin_user = schemas.UserCreate(
    #             email="admin@codeatlas.dev",
    #             username="admin",
    #             password="changeme123"
    #         )
    #         await crud.create_user(session, admin_user)
    #         print("✅ Created default admin user")
    
    print("📝 No initial data required (skipped)")


def main():
    """Main entry point."""
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