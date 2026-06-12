"""
SQLAlchemy table sketches — abstract entities, not real domain types.

The point of this file is to show *the shape* of a high-throughput schema:
where the indices go, what kind of pool config you want, how the read
panel reads from these tables. Production has different names and many
more columns.
"""
import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, BigInteger, String, Float,
    DateTime, ForeignKey, Index,
)
from sqlalchemy.orm import declarative_base, sessionmaker

DB_URL = os.getenv("DB_URL", "postgresql://user:pass@localhost:5432/demo")
engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
)
SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    s = SessionFactory()
    try:
        yield s
    finally:
        s.close()


def init_db():
    Base.metadata.create_all(bind=engine)


# ── Abstract tables (placeholders for whatever your real domain is) ──────────
class Participant(Base):
    """A generic actor in the system. Rename to whatever fits your domain."""
    __tablename__ = "participants"
    id          = Column(BigInteger, primary_key=True)
    handle      = Column(String(64), unique=True, index=True)
    score_a     = Column(Float, default=0.0)
    score_b     = Column(Float, default=0.0)
    updated_at  = Column(DateTime, default=datetime.utcnow, index=True)


class Event(Base):
    """Something that happened to a Participant. Replace with your real event."""
    __tablename__ = "events"
    id           = Column(BigInteger, primary_key=True)
    participant_id = Column(BigInteger, ForeignKey("participants.id"), index=True)
    kind         = Column(String(32), index=True)
    magnitude    = Column(Float)
    delta_score  = Column(Float)
    occurred_at  = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_events_participant_when", "participant_id", "occurred_at"),
    )


class Snapshot(Base):
    """A point-in-time read of some metric we keep open and rolling."""
    __tablename__ = "snapshots"
    id            = Column(BigInteger, primary_key=True)
    participant_id = Column(BigInteger, ForeignKey("participants.id"), index=True)
    kind          = Column(String(32))
    value_a       = Column(Float)
    value_b       = Column(Float)


class Gauge(Base):
    """Named numeric value, captured periodically."""
    __tablename__ = "gauges"
    id            = Column(BigInteger, primary_key=True)
    participant_id = Column(BigInteger, ForeignKey("participants.id"), index=True)
    name          = Column(String(64), index=True)
    value         = Column(Float)
    captured_at   = Column(DateTime, default=datetime.utcnow, index=True)


class ChangeLog(Base):
    """Append-only log of mutating calls — used for forensic replays."""
    __tablename__ = "change_log"
    id       = Column(BigInteger, primary_key=True)
    actor    = Column(String(64), index=True)
    action   = Column(String(32))
    target   = Column(BigInteger, index=True)
    at       = Column(DateTime, default=datetime.utcnow, index=True)
