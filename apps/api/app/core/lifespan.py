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
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))

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
        logger.error("redis unavailable at startup: %s", exc)

    yield

    await razorpay_client.close()
    await app.state.arq_pool.close()
    await app.state.redis.close()
    await engine.dispose()
