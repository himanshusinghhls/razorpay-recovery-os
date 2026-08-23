import asyncio
import sys

sys.path.insert(0, ".")

from apps.api.app.db.session import engine
from apps.api.app.db.models import Base

async def init_models():
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_models())
