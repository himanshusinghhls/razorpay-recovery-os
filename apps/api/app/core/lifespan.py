import logging
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from redis.asyncio import Redis

from apps.api.app.config import settings
from apps.api.app.db.session import engine
from integrations.razorpay.client import RazorpayClient

logger = logging.getLogger("recoveryos.lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    razorpay_client = RazorpayClient()
    app.state.razorpay = razorpay_client

    # Job queue. Previously this DSN was hardcoded to localhost, so REDIS_URL
    # in the environment was silently ignored and the app could not be pointed
    # at a managed Redis.
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))

    # A separate plain client for rate limits and idempotency keys. Keeping it
    # apart from the ARQ pool means queue backpressure cannot starve auth.
    app.state.redis = Redis.from_url(
        settings.redis_url,
        decode_responses=False,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
    )

    try:
        await app.state.redis.ping()
        logger.info("redis connected: %s", settings.redis_url.split("@")[-1])
    except Exception as exc:  # noqa: BLE001
        # Rate limiting fails open and idempotency degrades, but the API stays
        # up rather than refusing to boot on a dependency blip.
        logger.error("redis unavailable at startup: %s", exc)

    yield

    await razorpay_client.close()
    await app.state.arq_pool.close()
    # redis-py is pinned below 5 by arq, where the coroutine is close(), not aclose().
    await app.state.redis.close()
    await engine.dispose()
