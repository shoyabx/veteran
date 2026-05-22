from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.retrieval import RetrievalQuery


def replay_query(query_id: int, tenant_id: int | None = None) -> dict:
    db = SessionLocal()
    try:
        q = db.scalar(select(RetrievalQuery).where(RetrievalQuery.id == query_id))
        if q is None:
            return {'ok': False, 'error': 'query_not_found'}
        if tenant_id is not None and q.tenant_id != tenant_id:
            return {'ok': False, 'error': 'tenant_mismatch'}
        return {
            'ok': True,
            'query_id': q.id,
            'tenant_id': q.tenant_id,
            'query_text': q.query_text,
            'normalized_query': q.normalized_query,
            'filters': q.filter_payload,
            'top_k': q.top_k,
            'score_threshold': q.score_threshold,
            'created_at': str(q.created_at),
        }
    finally:
        db.close()
