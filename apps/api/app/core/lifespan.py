from contextlib import asynccontextmanager

from fastapi import FastAPI

from integrations.razorpay.client import RazorpayClient
from arq import create_pool
from arq.connections import RedisSettings


@asynccontextmanager
async def lifespan(app: FastAPI):
    razorpay_client = RazorpayClient()

    app.state.razorpay = razorpay_client

    redis_pool = await create_pool(RedisSettings.from_dsn("redis://localhost:6379/0"))
    app.state.arq_pool = redis_pool

    yield

    await razorpay_client.close()
    await redis_pool.close()
