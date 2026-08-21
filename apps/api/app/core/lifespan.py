from contextlib import asynccontextmanager

from fastapi import FastAPI

from integrations.razorpay.client import RazorpayClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    razorpay_client = RazorpayClient()

    app.state.razorpay = razorpay_client

    yield

    await razorpay_client.close()
