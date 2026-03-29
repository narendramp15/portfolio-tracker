"""In-memory rate limiter for auth endpoints.

Uses a sliding-window counter per (IP, endpoint) key.
Safe for single-process deployments (Render, Railway).  For multi-process
setups behind a load balancer, swap to Redis-backed storage.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request


class RateLimiter:
    """Simple sliding-window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _key(self, request: Request, suffix: str = "") -> str:
        client = request.client.host if request.client else "unknown"
        return f"{client}:{request.url.path}:{suffix}"

    def check(self, request: Request, suffix: str = "") -> None:
        """Raise 429 if the caller has exceeded the rate limit."""
        key = self._key(request, suffix)
        now = time.monotonic()

        with self._lock:
            timestamps = self._hits[key]
            # Prune old entries outside the window
            cutoff = now - self.window
            self._hits[key] = timestamps = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= self.max_requests:
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many requests. Try again in {self.window} seconds.",
                )
            timestamps.append(now)


# Pre-built limiters for auth endpoints
auth_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
register_rate_limiter = RateLimiter(max_requests=3, window_seconds=60)
password_reset_rate_limiter = RateLimiter(max_requests=3, window_seconds=300)
