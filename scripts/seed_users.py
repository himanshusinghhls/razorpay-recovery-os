"""
Seed the demo merchant and its user accounts.

Run with:
    PYTHONPATH=. ./apps/api/.venv/bin/python scripts/seed_users.py

Passwords come from the environment when set, and are otherwise generated
randomly and printed once. Nothing is hardcoded, so a seeded deployment never
ships with a known-good credential.
"""

import asyncio
import os
import secrets
import sys

from sqlalchemy import select

from apps.api.app.core.security import hash_password
from apps.api.app.db.models import Merchant, User, UserRole
from apps.api.app.db.session import AsyncSessionLocal, engine

DEMO_MERCHANT = {
    "merchant_id": "mrch_demo_recoveryos",
    "name": "Acme Commerce",
    "slug": "acme-commerce",
}

DEMO_USERS = [
    ("SEED_ADMIN_PASSWORD", "admin@acmecommerce.in", "Himanshu", UserRole.ADMIN),
    ("SEED_ANALYST_PASSWORD", "analyst@acmecommerce.in", "Anjali", UserRole.ANALYST),
    ("SEED_VIEWER_PASSWORD", "viewer@acmecommerce.in", "Krishna", UserRole.VIEWER),
]


async def seed() -> None:
    generated: list[tuple[str, str]] = []

    async with AsyncSessionLocal() as session:
        merchant = await session.get(Merchant, DEMO_MERCHANT["merchant_id"])
        if merchant is None:
            merchant = Merchant(**DEMO_MERCHANT)
            session.add(merchant)
            await session.flush()
            print(f"created merchant {merchant.merchant_id} ({merchant.name})")
        else:
            print(f"merchant {merchant.merchant_id} already exists")

        for env_var, email, full_name, role in DEMO_USERS:
            existing = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()

            if existing is not None:
                print(f"user {email} already exists — skipped")
                continue

            password = os.environ.get(env_var)
            if not password:
                password = secrets.token_urlsafe(12)
                generated.append((email, password))

            session.add(
                User(
                    merchant_id=merchant.merchant_id,
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password(password),
                    role=role,
                )
            )
            print(f"created {role.value:<8} {email}")

        await session.commit()

    await engine.dispose()

    if generated:
        print("\n" + "=" * 60)
        print("Generated passwords — shown once, not stored anywhere:")
        for email, password in generated:
            print(f"  {email:<24} {password}")
        print("=" * 60)
        print("Set SEED_ADMIN_PASSWORD / SEED_ANALYST_PASSWORD /")
        print("SEED_VIEWER_PASSWORD to choose them yourself instead.")


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    except Exception as exc:  # noqa: BLE001
        print(f"seed failed: {exc}", file=sys.stderr)
        sys.exit(1)
