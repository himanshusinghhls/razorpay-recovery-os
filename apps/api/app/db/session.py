from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.app.config import settings

db_url = settings.database_url.replace("postgresql://", "postgresql+psycopg://")

engine = create_async_engine(
    db_url,
    echo=False,
    # Sized for a single process; total DB connections is this x worker count,
    # which has to stay under Postgres max_connections.
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    # Recycle before common proxy/Postgres idle timeouts drop the socket.
    pool_recycle=settings.db_pool_recycle,
    # Cheap liveness check on checkout; without it, every connection in the
    # pool raises once after a database restart or failover.
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Request-scoped session.

    Rolls back on any unhandled exception so a failed request can never leave a
    half-applied transaction on a pooled connection for the next caller.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
