from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Simple token-bucket rate limiter for async contexts."""

    def __init__(self, rate: float = 30.0, period: float = 1.0):
        self._rate = rate
        self._period = period
        self._tokens = rate
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._rate, self._tokens + elapsed * (self._rate / self._period))
            self._last_refill = now

            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) * (self._period / self._rate)
                await asyncio.sleep(wait)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0
