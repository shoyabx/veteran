from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.models.ingestion import Mailbox
from app.models.indexing import IndexedChunk
from app.models.retrieval import (
    RetrievalQuery, RetrievalResult, CitationValidationFailure, RerankMetric, RetrievalTelemetry,
)
from app.services.embedding_provider import OpenAIEmbeddingProvider
from app.services.qdrant_client import TenantQdrant
from app.services.retrieval_query import normalize_query
from app.services.retrieval_filters import validate_filters, build_qdrant_filter
from app.services.retrieval_rerank import rerank_hits
from app.services.citation_validator import validate_citation_payload
from app.services.retrieval_confidence import compute_confidence
from app.services.evidence_assembly import assemble_evidence
from app.services.telemetry import Timer


def _assert_mailbox_scope(db: Session, tenant_id: int, mailbox_id: int | None) -> None:
    if mailbox_id is None:
        return
    mailbox = db.scalar(select(Mailbox).where(Mailbox.id == mailbox_id, Mailbox.tenant_id == tenant_id, Mailbox.is_active == True))
    if mailbox is None:
        raise ValueError('mailbox_not_found_or_not_owned')


def run_retrieval_query(
    db: Session,
    tenant_id: int,
    user_id: int,
    query_text: str,
    filters: dict | None,
    top_k: int,
    score_threshold: float,
    correlation_id: str,
) -> RetrievalQuery:
    model_name = settings.EMBEDDING_MODEL
    n = normalize_query(query_text, model_name)
    valid_filters = validate_filters(filters)
    mailbox_id = valid_filters.get('mailbox_id')
    _assert_mailbox_scope(db, tenant_id, mailbox_id)

    rq = RetrievalQuery(
        tenant_id=tenant_id,
        mailbox_id=mailbox_id,
        query_text=query_text,
        normalized_query=n.normalized_query,
        query_checksum=n.query_checksum,
        top_k=top_k,
        score_threshold=score_threshold,
        filter_payload=valid_filters,
        query_tokens=n.query_tokens,
        status='running',
        correlation_id=correlation_id,
    )
    db.add(rq)
    db.commit(); db.refresh(rq)

    p = OpenAIEmbeddingProvider(settings.OPENAI_API_KEY, batch_size=1)
    qdrant = TenantQdrant(settings.QDRANT_URL, settings.QDRANT_API_KEY or None)

    total_timer = Timer.begin()
    emb_timer = Timer.begin()
    emb = __import__('asyncio').run(p.embed([n.normalized_query], model_name=model_name))
    db.add(RetrievalTelemetry(tenant_id=tenant_id, query_id=rq.id, metric_name='query_embedding_latency_ms', metric_value=float(emb.latency_ms), tags=None, correlation_id=correlation_id))

    q_timer = Timer.begin()
    q_filter = build_qdrant_filter(tenant_id, valid_filters)
    hits = qdrant.search_vectors(tenant_id=tenant_id, query_vector=emb.vectors[0], top_k=top_k, score_threshold=score_threshold, filters=q_filter)
    db.add(RetrievalTelemetry(tenant_id=tenant_id, query_id=rq.id, metric_name='qdrant_latency_ms', metric_value=float(q_timer.elapsed_ms()), tags={'top_k': top_k}, correlation_id=correlation_id))

    mode = valid_filters.get('mode', 'mixed')
    mapped = []
    for h in hits:
        payload = h.payload or {}
        if mode == 'attachment' and payload.get('attachment_id') is None:
            continue
        if mode == 'email' and payload.get('attachment_id') is not None:
            continue
        mapped.append({'id': str(h.id), 'score': float(h.score), 'payload': payload})

    reranked = rerank_hits(mapped, valid_filters)

    persisted_rows = []
    rank = 1
    for r in reranked:
        payload = r['payload']
        ok, reason = validate_citation_payload(payload)
        if not ok:
            db.add(CitationValidationFailure(
                tenant_id=tenant_id,
                query_id=rq.id,
                vector_id=r['id'],
                chunk_id=payload.get('chunk_id'),
                failure_code='citation_invalid',
                failure_reason=reason or 'unknown',
            ))
            continue

        idx_chunk = db.scalar(select(IndexedChunk).where(IndexedChunk.tenant_id == tenant_id, IndexedChunk.chunk_id == payload.get('chunk_id')))
        if idx_chunk is None:
            db.add(CitationValidationFailure(
                tenant_id=tenant_id,
                query_id=rq.id,
                vector_id=r['id'],
                chunk_id=payload.get('chunk_id'),
                failure_code='orphan_chunk',
                failure_reason='indexed_chunk_not_found',
            ))
            continue

        citation_integrity = 1.0
        conf = compute_confidence(r.get('score', 0.0), r['rerank_score'], citation_integrity, evidence_density=min(1.0, len(reranked) / max(top_k, 1)))

        db.add(RerankMetric(
            tenant_id=tenant_id,
            query_id=rq.id,
            vector_id=r['id'],
            semantic_similarity=r['rerank_components']['semantic_similarity'],
            metadata_relevance=r['rerank_components']['metadata_relevance'],
            recency_weight=r['rerank_components']['recency_weight'],
            continuity_weight=r['rerank_components']['continuity_weight'],
            attachment_weight=r['rerank_components']['attachment_weight'],
            final_score=r['rerank_score'],
        ))

        row = RetrievalResult(
            tenant_id=tenant_id,
            query_id=rq.id,
            rank=rank,
            vector_id=r['id'],
            chunk_id=payload['chunk_id'],
            email_id=int(payload['email_id']),
            mailbox_id=int(payload['mailbox_id']),
            conversation_id=payload.get('conversation_id'),
            attachment_id=payload.get('attachment_id'),
            source_start_offset=int(payload['source_start_offset']),
            source_end_offset=int(payload['source_end_offset']),
            source_timestamp=datetime.fromisoformat(payload['source_timestamp']) if payload.get('source_timestamp') else None,
            vector_score=float(r['score']),
            rerank_score=float(r['rerank_score']),
            citation_integrity_score=float(conf['citation_integrity_score']),
            retrieval_confidence=float(conf['retrieval_confidence']),
            evidence_confidence=float(conf['evidence_confidence']),
            citation_payload=payload,
            is_stale_rejected=False,
        )
        db.add(row)
        persisted_rows.append(row)
        rank += 1

    rq.status = 'completed'
    db.add(RetrievalTelemetry(tenant_id=tenant_id, query_id=rq.id, metric_name='retrieval_total_latency_ms', metric_value=float(total_timer.elapsed_ms()), tags=None, correlation_id=correlation_id))
    db.add(RetrievalTelemetry(tenant_id=tenant_id, query_id=rq.id, metric_name='query_tokens', metric_value=float(n.query_tokens), tags=None, correlation_id=correlation_id))
    db.commit(); db.refresh(rq)
    return rq


def get_query_results(db: Session, tenant_id: int, query_id: int) -> list[RetrievalResult]:
    return db.scalars(select(RetrievalResult).where(RetrievalResult.tenant_id == tenant_id, RetrievalResult.query_id == query_id).order_by(RetrievalResult.rank.asc())).all()


def get_evidence_bundle(db: Session, tenant_id: int, query_id: int) -> dict:
    rows = get_query_results(db, tenant_id, query_id)
    payload = []
    for r in rows:
        payload.append({
            'rank': r.rank,
            'vector_id': r.vector_id,
            'chunk_id': r.chunk_id,
            'retrieval_confidence': r.retrieval_confidence,
            'evidence_confidence': r.evidence_confidence,
            'citation_integrity_score': r.citation_integrity_score,
            'citation_payload': r.citation_payload,
        })
    return assemble_evidence(payload)
