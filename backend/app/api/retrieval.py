from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta

from app.core.config import settings
from app.db.session import get_db
from app.models.retrieval import RetrievalQuery
from app.schemas.retrieval import (
    RetrievalQueryRequest, RetrievalQueryResponse, RetrievalQueryStatusResponse,
    RetrievalResultItem, RetrievalEvidenceResponse,
)
from app.services.retrieval_service import run_retrieval_query, get_query_results, get_evidence_bundle

router = APIRouter(prefix='/retrieval', tags=['retrieval'])
_RATE_BUCKET: dict[int, list[datetime]] = {}


def _check_rate_limit(tenant_id: int):
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=1)
    arr = [t for t in _RATE_BUCKET.get(tenant_id, []) if t >= window_start]
    if len(arr) >= settings.RETRIEVAL_RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail='retrieval_rate_limit_exceeded')
    arr.append(now)
    _RATE_BUCKET[tenant_id] = arr


@router.post('/query', response_model=RetrievalQueryResponse)
def retrieval_query(payload: RetrievalQueryRequest, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    _check_rate_limit(user['tenant_id'])
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    q = run_retrieval_query(
        db=db,
        tenant_id=user['tenant_id'],
        user_id=user['user_id'],
        query_text=payload.query,
        filters=payload.filters,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        correlation_id=correlation_id,
        synthesize=payload.synthesize,
    )
    return RetrievalQueryResponse(query_id=q.id, status=q.status)


@router.get('/query/{query_id}', response_model=RetrievalQueryStatusResponse)
def retrieval_query_status(query_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    q = db.scalar(select(RetrievalQuery).where(RetrievalQuery.id == query_id, RetrievalQuery.tenant_id == user['tenant_id']))
    if q is None:
        raise HTTPException(status_code=404, detail='retrieval_query_not_found')

    rows = get_query_results(db, user['tenant_id'], query_id)
    results = [RetrievalResultItem(
        rank=r.rank,
        vector_id=r.vector_id,
        chunk_id=r.chunk_id,
        email_id=r.email_id,
        mailbox_id=r.mailbox_id,
        conversation_id=r.conversation_id,
        attachment_id=r.attachment_id,
        vector_score=r.vector_score,
        rerank_score=r.rerank_score,
        retrieval_confidence=r.retrieval_confidence,
        evidence_confidence=r.evidence_confidence,
        citation_integrity_score=r.citation_integrity_score,
        citation_payload=r.citation_payload,
    ) for r in rows]

    return RetrievalQueryStatusResponse(
        query_id=q.id,
        status=q.status,
        created_at=q.created_at,
        results=results,
        answer=q.answer,
        evidence_snapshot_hash=q.evidence_snapshot_hash,
        retrieval_version=q.retrieval_version,
        synthesis_version=q.synthesis_version,
        citation_checksum=q.citation_checksum,
        vector_index_version=q.vector_index_version,
        unsupported_claim_risk=q.unsupported_claim_risk,
        retrieval_coverage_score=q.retrieval_coverage_score,
        synthesis_validation_status=q.synthesis_validation_status,
    )


@router.get('/evidence/{query_id}', response_model=RetrievalEvidenceResponse)
def retrieval_evidence(query_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    q = db.scalar(select(RetrievalQuery).where(RetrievalQuery.id == query_id, RetrievalQuery.tenant_id == user['tenant_id']))
    if q is None:
        raise HTTPException(status_code=404, detail='retrieval_query_not_found')
    evidence = get_evidence_bundle(db, user['tenant_id'], query_id)
    return RetrievalEvidenceResponse(query_id=query_id, evidence=evidence)
