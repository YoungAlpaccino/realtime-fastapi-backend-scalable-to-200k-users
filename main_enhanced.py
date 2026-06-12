"""
Sketch: realtime backend — read/write split, HMAC-signed mutations,
in-process cache, scheduler tick.

DEMONSTRATION ONLY. Most function bodies are stubs that show *where* the
real logic goes, not what it is.
"""
import os
import time
import hmac
import hashlib
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from models import get_db, init_db
from schemas import (
    MutateRequest, MutateAck, ParticipantView,
    HealthResponse, RankingResponse,
)
from ops import Repository, write_changelog
from cache import RankingCache


# ── Tunables ────────────────────────────────────────────────────────────────
CACHE_TTL_SECONDS         = 1800
SIGNATURE_REPLAY_WINDOW   = 3000      # ms
LEADERBOARD_REFRESH_EVERY = 60        # seconds

API_SECRET        = os.getenv("API_SECRET", "replace-me")
DISABLE_SIGNATURE = os.getenv("DISABLE_SIGNATURE", "false").lower() == "true"

logger    = logging.getLogger(__name__)
cache     = RankingCache(ttl_seconds=CACHE_TTL_SECONDS)
scheduler = AsyncIOScheduler()


# ── HMAC guard (pseudo) ──────────────────────────────────────────────────────
def verify_signature(
    x_signature: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None),
):
    """Sketch: real version also pins the verb + path into the signature base."""
    if DISABLE_SIGNATURE:
        return True
    if not x_signature or not x_timestamp:
        raise HTTPException(401, "missing signature headers")

    try:
        ts = int(x_timestamp)
    except ValueError:
        raise HTTPException(401, "bad timestamp")

    if abs(int(time.time() * 1000) - ts) > SIGNATURE_REPLAY_WINDOW:
        raise HTTPException(401, "timestamp out of window")

    expected = hmac.new(
        API_SECRET.encode(), x_timestamp.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, x_signature):
        raise HTTPException(401, "bad signature")
    return True


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    await cache.warm()
    scheduler.add_job(
        cache.refresh, "interval",
        seconds=LEADERBOARD_REFRESH_EVERY, id="ranking_refresh",
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="realtime-backend-sketch", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# ── Read endpoints (cache-first) ─────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", uptime=time.time())


@app.get("/ranking", response_model=RankingResponse)
async def ranking(top: int = 100):
    rows = await cache.top(top)
    return RankingResponse(rows=rows, served_from="cache")


@app.get("/participants/{pid}", response_model=ParticipantView)
async def show_participant(pid: int, db: Session = Depends(get_db)):
    row = Repository.get_participant(db, pid)
    if row is None:
        raise HTTPException(404, "not found")
    return ParticipantView.from_row(row)


# ── Mutation endpoint (signature-gated) ──────────────────────────────────────
@app.post("/participants/mutate", response_model=MutateAck)
async def mutate_participant(
    payload: MutateRequest,
    _ok: bool = Depends(verify_signature),
    db: Session = Depends(get_db),
):
    """
    Pseudo-flow:
        1. validate signed payload (decorator above)
        2. delegate to repository
        3. append to change_log
        4. invalidate the affected cache slot
    """
    try:
        row = Repository.upsert_participant(db, payload)
        write_changelog(db, actor=payload.actor, action="mutate", target=row.id)
        cache.invalidate(row.id)
        return MutateAck(ok=True, target_id=row.id)
    except Exception:
        logger.exception("mutation failed")
        raise HTTPException(500, "mutation failed")
