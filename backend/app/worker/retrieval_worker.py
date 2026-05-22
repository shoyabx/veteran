import asyncio
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.retrieval import RetrievalQuery
from app.services.telemetry import log_telemetry


async def run_once():
    db = SessionLocal()
    try:
        queued = db.scalars(select(RetrievalQuery).where(RetrievalQuery.status == 'queued').order_by(RetrievalQuery.id.asc()).limit(10)).all()
        for q in queued:
            # Retrieval currently executes synchronously at API boundary; worker scaffold reserved for async orchestration.
            q.status = 'deferred'
            log_telemetry('retrieval_worker_deferred_query', {'query_id': q.id, 'tenant_id': q.tenant_id})
        db.commit()
    finally:
        db.close()


async def loop_forever():
    while True:
        await run_once()
        await asyncio.sleep(5)


if __name__ == '__main__':
    asyncio.run(loop_forever())
