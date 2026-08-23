import asyncio
import sys
sys.path.insert(0, ".")

from apps.api.app.db.session import engine
from apps.api.app.db.models import Base

async def reset():
    print("Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("Recreating all tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("Database reset complete.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset())
