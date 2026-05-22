from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.ingestion import MailboxCreateRequest, MailboxResponse, SyncStartRequest, SyncStartResponse, IngestionStatusResponse
from app.models.ingestion import Mailbox, IngestionJob
from app.services.ingestion_service import create_ingestion_job

router = APIRouter(prefix='/ingestion', tags=['ingestion'])

@router.post('/mailboxes', response_model=MailboxResponse)
def create_mailbox(payload: MailboxCreateRequest, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    row = Mailbox(
        tenant_id=user['tenant_id'],
        user_id=user['user_id'],
        provider='microsoft_graph',
        provider_mailbox_id=payload.provider_mailbox_id,
        email_address=payload.email_address,
    )
    db.add(row)
    db.commit(); db.refresh(row)
    return row

@router.post('/sync/start', response_model=SyncStartResponse)
def start_sync(payload: SyncStartRequest, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    job = create_ingestion_job(db, tenant_id=user['tenant_id'], mailbox_id=payload.mailbox_id, correlation_id=correlation_id)
    return SyncStartResponse(job_id=job.id, status=job.status)

@router.get('/jobs/{job_id}', response_model=IngestionStatusResponse)
def get_job(job_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    row = db.query(IngestionJob).filter(IngestionJob.id == job_id, IngestionJob.tenant_id == user['tenant_id']).first()
    if row is None:
        raise HTTPException(status_code=404, detail='ingestion_job_not_found')
    return IngestionStatusResponse(job_id=row.id, status=row.status, started_at=row.started_at, finished_at=row.finished_at)
