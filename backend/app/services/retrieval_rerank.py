from __future__ import annotations

from datetime import datetime, timezone


def _recency_weight(source_ts: str | None) -> float:
    if not source_ts:
        return 0.5
    try:
        dt = datetime.fromisoformat(source_ts.replace('Z', '+00:00'))
    except Exception:
        return 0.5
    age_days = max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 86400)
    return max(0.2, 1.0 - min(age_days / 365.0, 0.8))


def rerank_hits(hits: list[dict], filters: dict) -> list[dict]:
    out = []
    seen_chunks = set()
    for h in hits:
        payload = h.get('payload', {})
        chunk_id = payload.get('chunk_id')
        if not chunk_id or chunk_id in seen_chunks:
            continue

        vector_score = float(h.get('score', 0.0))
        metadata_relevance = 1.0
        if filters.get('conversation_id') and payload.get('conversation_id') != filters.get('conversation_id'):
            metadata_relevance = 0.3
        recency = _recency_weight(payload.get('source_timestamp'))
        continuity = 1.0 if payload.get('conversation_id') else 0.6
        attachment_rel = 1.0 if payload.get('attachment_id') else 0.8

        final = (0.55 * vector_score) + (0.15 * metadata_relevance) + (0.15 * recency) + (0.10 * continuity) + (0.05 * attachment_rel)
        row = {
            **h,
            'rerank_components': {
                'semantic_similarity': vector_score,
                'metadata_relevance': metadata_relevance,
                'recency_weight': recency,
                'continuity_weight': continuity,
                'attachment_weight': attachment_rel,
            },
            'rerank_score': final,
        }
        seen_chunks.add(chunk_id)
        out.append(row)

    out.sort(key=lambda x: (x['rerank_score'], x.get('score', 0.0)), reverse=True)
    return out
