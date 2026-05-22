import asyncio
import logging
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.ingestion import IngestionJob
from app.services.ingestion_service import run_mailbox_delta_sync

logger = logging.getLogger('ingestion-worker')

async def run_once():
    db = SessionLocal()
    try:
        queued = db.scalar(select(IngestionJob).where(IngestionJob.status == 'queued').order_by(IngestionJob.id.asc()).limit(1))
        if not queued:
            return
        await run_mailbox_delta_sync(db, queued.tenant_id, queued.mailbox_id, queued.correlation_id, job=queued)
    finally:
        db.close()

async def loop_forever():
    while True:
        await run_once()
        await asyncio.sleep(3)

if __name__ == '__main__':
    asyncio.run(loop_forever())
