"""Per-IP sliding-window rate limit, in memory.

In memory is enough for one container (the deploy target). It resets on
restart, which is acceptable for a demo's cost protection.
"""

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request


class RateLimiter:
    def __init__(self, limit: int, window_s: float, clock: Callable[[], float] = time.monotonic):
        self.limit = limit
        self.window_s = window_s
        self.clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> float | None:
        """Record a hit. Return None if allowed, else seconds until the next slot opens."""
        now = self.clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window_s:
                hits.popleft()
            if len(hits) >= self.limit:
                return round(self.window_s - (now - hits[0]), 1)
            hits.append(now)
            return None


def client_ip(request: Request, trusted_proxies: int = 1) -> str:
    """The client address as seen by our own proxy.

    X-Forwarded-For is "client, proxy1, proxy2...". Everything left of what our
    trusted proxies appended is client-controlled and can be spoofed to dodge
    the limit, so read the entry `trusted_proxies` places from the right.
    """
    forwarded = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",")]
    forwarded = [h for h in forwarded if h]
    if trusted_proxies and forwarded:
        return forwarded[-min(trusted_proxies, len(forwarded))]
    return request.client.host if request.client else "unknown"
