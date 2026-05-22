from app.services.retrieval_query import normalize_query


def test_query_normalization_deterministic():
    a = normalize_query('  Hello   WORLD ', 'text-embedding-3-small')
    b = normalize_query('hello world', 'text-embedding-3-small')
    assert a.normalized_query == 'hello world'
    assert a.query_checksum == b.query_checksum
    assert a.query_tokens > 0
