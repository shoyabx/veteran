import asyncio
import os
import socket
from datetime import datetime
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.indexing import EmbeddingJob, WorkerHeartbeat
from app.services.indexing_service import run_embedding_job
from app.services.dead_letter import move_to_dead_letter
from app.core.config import settings

WORKER_NAME = 'embedding-worker'
INSTANCE_ID = f"{socket.gethostname()}-{os.getpid()}"


def upsert_heartbeat(status: str, tenant_id: int | None = None, payload: dict | None = None):
    db = SessionLocal()
    try:
        hb = db.scalar(select(WorkerHeartbeat).where(WorkerHeartbeat.worker_name == WORKER_NAME, WorkerHeartbeat.worker_instance_id == INSTANCE_ID))
        if hb is None:
            hb = WorkerHeartbeat(worker_name=WORKER_NAME, worker_instance_id=INSTANCE_ID, status=status, tenant_id=tenant_id, meta_payload=payload)
            db.add(hb)
        else:
            hb.status = status
            hb.tenant_id = tenant_id
            hb.meta_payload = payload
            hb.last_seen_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


async def run_once():
    db = SessionLocal()
    job = None
    try:
        upsert_heartbeat('idle')
        job = db.scalar(select(EmbeddingJob).where(EmbeddingJob.status == 'queued').order_by(EmbeddingJob.id.asc()).limit(1))
        if not job:
            return
        upsert_heartbeat('running', tenant_id=job.tenant_id, payload={'job_id': job.id})
        started = datetime.utcnow()
        result = await asyncio.wait_for(run_embedding_job(db, job), timeout=settings.WORKER_JOB_TIMEOUT_SECONDS)
        if result.status == 'failed' and result.retry_count >= settings.WORKER_MAX_RETRIES:
            move_to_dead_letter(db, tenant_id=result.tenant_id, job_type='embedding', payload={'job_id': result.id}, reason='max_retries_exceeded', correlation_id=result.correlation_id)
        upsert_heartbeat('idle', tenant_id=result.tenant_id, payload={'job_id': result.id, 'duration_s': int((datetime.utcnow()-started).total_seconds())})
    except asyncio.TimeoutError:
        if job:
            job.status = 'failed'
            job.retry_count += 1
            db.commit()
            move_to_dead_letter(db, tenant_id=job.tenant_id, job_type='embedding', payload={'job_id': job.id}, reason='job_timeout', correlation_id=job.correlation_id)
        upsert_heartbeat('error', payload={'reason': 'timeout'})
    except Exception as e:
        upsert_heartbeat('error', payload={'error': str(e)})
    finally:
        db.close()


async def loop_forever():
    while True:
        await run_once()
        await asyncio.sleep(3)


if __name__ == '__main__':
    asyncio.run(loop_forever())
