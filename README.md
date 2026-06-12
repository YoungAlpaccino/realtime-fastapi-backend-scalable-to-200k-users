# Realtime FastAPI Backend — Scalable to 200k Concurrent Users

> ## NOTE
> **The code in this repository is a demonstration of the architecture and is not a working service.**
> Field names, entity names, and column lists have been deliberately abstracted; any vendor SDKs,
> broker integrations, secrets, and operational shims have been removed. Treat the files here as
> a structural blueprint, not as something you can `pip install -r` and run.
>
> If you fork it, you are expected to replace the abstract entities (`Participant`, `Event`,
> `Snapshot`, `Gauge`) with your real domain model, wire your own data sources, and harden the
> operational layer for your environment.

---

## What this project demonstrates

A high-throughput FastAPI service that can sustain real-time read traffic for a large user base
(target ~200k concurrent) while a separate write path keeps the underlying state fresh.

The architecture rests on five ideas:

1. **Strict read/write separation** — the public read path never blocks on the write path.
2. **Connection pooling with overflow** — every DB session is borrowed from a tuned pool
   (`pool_size=20`, `max_overflow=40`, `pool_pre_ping=True`).
3. **In-process TTL/LRU cache** — hot endpoints (rankings, aggregates) hit memory, not the DB.
4. **HMAC-signed mutations** — every write endpoint is signature-verified with a replay window.
5. **Multi-process fan-out** — a launcher spawns one uvicorn worker per shard so one box can
   serve multiple isolated read panels in parallel.

## High-level diagram

```
      ┌──────────────┐         ┌──────────────────┐
HTTP ─►│  FastAPI     │ ──────►│  In-process LRU  │── miss ──┐
      │  (read path) │         │  + TTL cache     │          │
      └──────────────┘         └──────────────────┘          ▼
             ▲                                       ┌──────────────┐
             │ HMAC sig check                        │  Postgres    │
             │                                       │  read-only   │
      ┌──────────────┐                               └──────────────┘
HTTP ─►│  FastAPI     │                                     ▲
      │  (write path)│ ──── async scheduler ────► writers ──┘
      └──────────────┘
```

## Files in this showcase

| File | What it shows |
|------|---------------|
| `main_enhanced.py` | App wiring, lifespan, HMAC middleware, router mounting. |
| `models.py`        | SQLAlchemy sketches with **abstract** entities (Participant, Event, Snapshot, Gauge, ChangeLog). |
| `schemas.py`       | Pydantic request/response contracts. |
| `cache.py`         | TTL + LRU ranking cache with a background refresh tick. |
| `ops.py`           | Thin repository layer + change-log append. |
| `cron_jobs.py`     | APScheduler-based recurring jobs. |
| `run_servers.py`   | Multi-process launcher (one uvicorn per shard). |
| `stress_test.py`   | Asyncio stress harness that produced the 200k concurrent numbers. |
| `requirements.txt` | Unpinned dependency surface. |

## What is intentionally not here

- Real domain entities and column names
- Any vendor SDK / external integration
- Real authentication, secrets, or `.env` material
- Operational glue (deploy scripts, systemd units, monitoring exporters)

The point is the *shape*, not a fork-and-deploy.
