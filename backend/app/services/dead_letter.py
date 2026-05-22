from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.indexing import DeadLetterJob


def move_to_dead_letter(db: Session, tenant_id: int, job_type: str, payload: dict, reason: str, correlation_id: str) -> DeadLetterJob:
    row = DeadLetterJob(
        tenant_id=tenant_id,
        job_type=job_type,
        payload=payload,
        reason=reason,
        correlation_id=correlation_id,
        status='open',
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
