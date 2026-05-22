from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.indexing import EmbeddingJob
from app.schemas.indexing import IndexMailboxRequest, IndexJobResponse, IndexJobStatusResponse
from app.services.indexing_service import create_embedding_job, assert_mailbox_scope

router = APIRouter(prefix='/indexing', tags=['indexing'])

@router.post('/jobs', response_model=IndexJobResponse)
def create_job(payload: IndexMailboxRequest, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    assert_mailbox_scope(db, user['tenant_id'], payload.mailbox_id)
    corr = getattr(request.state, 'correlation_id', 'unknown')
    job = create_embedding_job(db, user['tenant_id'], payload.mailbox_id, payload.provider, payload.model_name, corr)
    return IndexJobResponse(job_id=job.id, status=job.status)

@router.get('/jobs/{job_id}', response_model=IndexJobStatusResponse)
def get_job(job_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    row = db.query(EmbeddingJob).filter(EmbeddingJob.id == job_id, EmbeddingJob.tenant_id == user['tenant_id']).first()
    if row is None:
        raise HTTPException(status_code=404, detail='embedding_job_not_found')
    return IndexJobStatusResponse(job_id=row.id, status=row.status, started_at=row.started_at, finished_at=row.finished_at)
