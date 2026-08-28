"""
Initialize all database tables.

Run with:
    PYTHONPATH=. python scripts/init_db.py
"""

import asyncio
import os
import subprocess
import sys

async def init_db():
    print("Running database migrations via Alembic...")
    
    api_dir = os.path.join(os.getcwd(), "apps", "api")
    alembic_bin = os.path.join(api_dir, ".venv", "bin", "alembic")
    
    subprocess.run(
        [alembic_bin, "-c", "alembic.ini", "upgrade", "head"], 
        cwd=api_dir,
        env={**os.environ, "PYTHONPATH": os.path.join(os.getcwd())},
        check=True
    )
    print("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
