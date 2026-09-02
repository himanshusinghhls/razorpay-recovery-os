"""
Distributed rate limiting backed by Redis.

Replaces the two process-local dicts this app used to carry (one in
middleware.py, one in routes/recoveries.py). Those were wrong in three ways:
they never evicted keys, so memory grew without bound; each uvicorn worker kept
its own counters, so the real limit was N x the configured value; and nothing
was shared across hosts.

This uses a fixed-window counter incremented via a single pipelined INCR/EXPIRE
round trip. Fixed windows allow a burst at a window boundary, which is an
acceptable trade for the cost — this is abuse protection, not billing.

Redis being unreachable must not take the API down, so failures here fail open
and are logged.
"""

import logging
import time
from dataclasses import dataclass

from redis.asyncio import Redis

logger = logging.getLogger("recoveryos.ratelimit")


@dataclass(frozen=True)
class RateLimitVerdict:
    allowed: bool
    limit: int
    remaining: int
    reset_after: int


async def check_rate_limit(
    redis: Redis | None,
    *,
    identity: str,
    scope: str,
    limit: int,
    window_seconds: int = 60,
) -> RateLimitVerdict:
    if redis is None:
        return RateLimitVerdict(True, limit, limit, window_seconds)

    now = int(time.time())
    window_start = now - (now % window_seconds)
    key = f"rl:{scope}:{identity}:{window_start}"

    try:
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds + 5)
        used, _ = await pipe.execute()
    except Exception as exc:  # noqa: BLE001 - availability beats strictness here
        logger.warning("rate limiter unavailable, failing open: %s", exc)
        return RateLimitVerdict(True, limit, limit, window_seconds)

    used = int(used)
    reset_after = window_start + window_seconds - now
    return RateLimitVerdict(
        allowed=used <= limit,
        limit=limit,
        remaining=max(0, limit - used),
        reset_after=max(1, reset_after),
    )
