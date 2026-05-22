import asyncio
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.ingestion import Mailbox
from app.models.indexing import EmbeddingJob
from app.services.indexing_service import create_embedding_job

async def schedule_once():
    db = SessionLocal()
    try:
        mailboxes = db.scalars(select(Mailbox).where(Mailbox.is_active == True).limit(20)).all()
        for m in mailboxes:
            existing = db.scalar(select(EmbeddingJob).where(EmbeddingJob.tenant_id == m.tenant_id, EmbeddingJob.mailbox_id == m.id, EmbeddingJob.status.in_(['queued', 'running'])).limit(1))
            if existing:
                continue
            create_embedding_job(db, m.tenant_id, m.id, provider='openai', model_name='text-embedding-3-small', correlation_id='scheduler')
    finally:
        db.close()

async def loop_forever():
    while True:
        await schedule_once()
        await asyncio.sleep(60)

if __name__ == '__main__':
    asyncio.run(loop_forever())
