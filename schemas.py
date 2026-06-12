"""
Pydantic contracts — kept intentionally thin.

These are sketches: every real field is a placeholder name. The interesting
part is the *shape* (request → ack, ack → audit-write, audit → cache-invalidate),
not the field list.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    uptime: float


class MutateRequest(BaseModel):
    target_id: int
    actor: str
    fields: dict = Field(default_factory=dict, description="opaque k/v patch")


class MutateAck(BaseModel):
    ok: bool
    target_id: int


class ParticipantView(BaseModel):
    id: int
    handle: str
    score_a: float
    score_b: float

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row.id, handle=row.handle,
            score_a=row.score_a, score_b=row.score_b,
        )


class RankRow(BaseModel):
    rank: int
    target_id: int
    score: float


class RankingResponse(BaseModel):
    rows: List[RankRow]
    served_from: str
