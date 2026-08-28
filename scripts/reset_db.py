import asyncio
import sys
sys.path.insert(0, ".")

from apps.api.app.db.session import engine
from apps.api.app.db.models import Base

async def reset():
    print("Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("Running Alembic upgrade...")
    await engine.dispose()
    
    import subprocess
    import os
    api_dir = os.path.join(os.getcwd(), "apps", "api")
    alembic_bin = os.path.join(api_dir, ".venv", "bin", "alembic")
    subprocess.run(
        [alembic_bin, "-c", "alembic.ini", "upgrade", "head"], 
        cwd=api_dir,
        env={**os.environ, "PYTHONPATH": os.path.join(os.getcwd())},
        check=True
    )
    print("Database reset complete.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset())
