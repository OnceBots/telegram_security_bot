import asyncio, time
from collections import defaultdict, deque

class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[int, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: int) -> bool:
        now = time.monotonic(); cutoff = now - self.window_seconds
        async with self._lock:
            queue = self._events[key]
            while queue and queue[0] < cutoff: queue.popleft()
            if len(queue) >= self.limit: return False
            queue.append(now)
            return True

    async def cleanup(self) -> None:
        now = time.monotonic(); cutoff = now - self.window_seconds
        async with self._lock:
            stale=[]
            for key, queue in self._events.items():
                while queue and queue[0] < cutoff: queue.popleft()
                if not queue: stale.append(key)
            for key in stale: self._events.pop(key, None)
