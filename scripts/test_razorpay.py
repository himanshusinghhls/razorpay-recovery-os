import asyncio
import sys

sys.path.insert(0, ".")

from integrations.razorpay.client import RazorpayClient


async def main():
    client = RazorpayClient()

    try:
        response = await client.client.get("/payments")

        print("HTTP status:", response.status_code)

        if response.status_code == 200:
            print("Razorpay authentication: SUCCESS")
            data = response.json()
            print("Response keys:", list(data.keys()))
        else:
            print("Razorpay authentication/request failed")
            print("Response:", response.text[:500])

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
