"""
TTL + LRU ranking cache (sketch).

This is the load-shield in front of the DB. Real implementation has
sharded slots, a background prefetcher, and a bloom filter for negative
hits. Here we keep it deliberately simple to make the pattern visible.
"""
import time
import asyncio
from collections import OrderedDict
from typing import List


class RankingCache:
    def __init__(self, ttl_seconds: int = 1800, dirty_cap: int = 10_000):
        self._ttl       = ttl_seconds
        self._dirty_cap = dirty_cap
        self._rows: List[dict] = []
        self._loaded_at = 0.0
        self._lock = asyncio.Lock()
        self._dirty: OrderedDict = OrderedDict()

    async def warm(self):
        await self.refresh()

    async def refresh(self):
        """Replace the in-memory slice with a fresh ordered cut from the DB."""
        async with self._lock:
            self._rows = await self._fetch_ordered_slice()
            self._loaded_at = time.time()
            self._dirty.clear()

    async def top(self, n: int):
        if time.time() - self._loaded_at > self._ttl:
            await self.refresh()
        return self._rows[:n]

    def invalidate(self, target_id: int):
        self._dirty[target_id] = True
        while len(self._dirty) > self._dirty_cap:
            self._dirty.popitem(last=False)

    # ── stub ─────────────────────────────────────────────────────────────────
    async def _fetch_ordered_slice(self):
        """DEMO stub. Real impl is `SELECT ... ORDER BY score LIMIT n` from
        a materialized view that the cron pipeline keeps fresh."""
        return [
            {"rank": i + 1, "target_id": 1000 + i, "score": 100.0 - i}
            for i in range(100)
        ]
