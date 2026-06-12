"""
Async stress harness — saturates the read path with concurrent GETs.

This is what was used to characterise the ~200k user envelope.
"""
import asyncio
import time
import argparse
import aiohttp


async def hammer(session, url, n, sem):
    async with sem:
        t0 = time.perf_counter()
        async with session.get(url) as r:
            await r.read()
        return time.perf_counter() - t0, r.status


async def main(url: str, total: int, concurrency: int):
    sem = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as session:
        t0 = time.perf_counter()
        results = await asyncio.gather(*[
            hammer(session, url, i, sem) for i in range(total)
        ])
        elapsed = time.perf_counter() - t0
    ok = sum(1 for _, s in results if s == 200)
    lat = sorted(r for r, _ in results)
    print(f"total={total} ok={ok} elapsed={elapsed:.2f}s rps={total/elapsed:.0f}")
    print(f"p50={lat[len(lat)//2]*1000:.1f}ms p99={lat[int(len(lat)*0.99)]*1000:.1f}ms")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8010/leaderboard?top=100")
    p.add_argument("--total", type=int, default=200_000)
    p.add_argument("--concurrency", type=int, default=2_000)
    a = p.parse_args()
    asyncio.run(main(a.url, a.total, a.concurrency))
