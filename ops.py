"""
Thin repository layer (sketch).

Every DB-touching call goes through here so tracing, retries, and pool
swap-outs all happen in one place. The bodies below are deliberately
shallow — production code adds idempotency keys, optimistic locking, etc.
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select
from models import Participant, ChangeLog

logger = logging.getLogger(__name__)


class Repository:
    @staticmethod
    def get_participant(db: Session, pid: int):
        return db.execute(
            select(Participant).where(Participant.id == pid)
        ).scalar_one_or_none()

    @staticmethod
    def upsert_participant(db: Session, payload):
        row = db.get(Participant, payload.target_id)
        if row is None:
            row = Participant(id=payload.target_id, handle=f"p{payload.target_id}")
            db.add(row)
        # pseudo: apply opaque patch fields onto the row
        for k, v in (payload.fields or {}).items():
            if hasattr(row, k):
                setattr(row, k, v)
        db.commit()
        db.refresh(row)
        return row


def write_changelog(db: Session, actor: str, action: str, target: int):
    db.add(ChangeLog(actor=actor, action=action, target=target))
    db.commit()
