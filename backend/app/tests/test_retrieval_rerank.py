from app.services.retrieval_rerank import rerank_hits


def test_rerank_is_deterministic_and_dedupes_chunk_ids():
    hits = [
        {'id': 'v1', 'score': 0.8, 'payload': {'chunk_id': 'c1', 'conversation_id': 't1', 'source_timestamp': '2026-01-01T00:00:00', 'attachment_id': None}},
        {'id': 'v2', 'score': 0.7, 'payload': {'chunk_id': 'c1', 'conversation_id': 't1', 'source_timestamp': '2026-01-02T00:00:00', 'attachment_id': None}},
        {'id': 'v3', 'score': 0.6, 'payload': {'chunk_id': 'c2', 'conversation_id': 't1', 'source_timestamp': '2026-01-03T00:00:00', 'attachment_id': 10}},
    ]
    a = rerank_hits(hits, {'conversation_id': 't1'})
    b = rerank_hits(hits, {'conversation_id': 't1'})
    assert [x['id'] for x in a] == [x['id'] for x in b]
    assert len(a) == 2
