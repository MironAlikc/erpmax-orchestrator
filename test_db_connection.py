"""
Test database connection script
Run: python test_db_connection.py
"""

import asyncio
from sqlalchemy import text
from app.core.database import engine, AsyncSessionLocal
from app.models import Base


async def test_connection():
    """Test database connection and display info"""
    print("🔍 Testing database connection...")

    try:
        async with engine.begin() as conn:
            # Test connection
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL!")
            print(f"   Version: {version}\n")

            # Check if tables exist
            result = await conn.execute(
                text(
                    """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """
                )
            )
            tables = result.fetchall()

            if tables:
                print(f"📊 Found {len(tables)} tables:")
                for table in tables:
                    print(f"   - {table[0]}")
            else:
                print("⚠️  No tables found. Run migrations with: alembic upgrade head")

            print("\n✅ Database connection test successful!")

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise
    finally:
        await engine.dispose()


async def test_models_import():
    """Test that all models can be imported"""
    print("\n🔍 Testing models import...")

    try:
        from app.models import (
            User,
            Tenant,
            UserTenant,
            Plan,
            Subscription,
            PaymentEvent,
            Base,
        )

        tables = Base.metadata.tables.keys()
        print(f"✅ Successfully imported {len(tables)} models:")
        for table_name in sorted(tables):
            print(f"   - {table_name}")

    except Exception as e:
        print(f"❌ Models import failed: {e}")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("ERPMax Orchestrator - Database Connection Test")
    print("=" * 60 + "\n")

    # Test models import
    asyncio.run(test_models_import())

    # Test database connection
    asyncio.run(test_connection())

    print("\n" + "=" * 60)
    print("All tests passed! 🎉")
    print("=" * 60)
