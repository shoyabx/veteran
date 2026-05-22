from app.services.citation_validator import validate_citation_payload


def test_citation_validator_accepts_complete_payload():
    ok, reason = validate_citation_payload({
        'tenant_id': 1,
        'mailbox_id': 1,
        'email_id': 1,
        'conversation_id': 'c1',
        'chunk_id': 'abc',
        'source_start_offset': 0,
        'source_end_offset': 10,
        'source_timestamp': '2026-01-01T00:00:00',
        'content_version': 1,
        'semantic_version': '2.1',
    })
    assert ok is True
    assert reason is None


def test_citation_validator_rejects_missing_lineage():
    ok, reason = validate_citation_payload({'tenant_id': 1})
    assert ok is False
    assert reason.startswith('missing_')
