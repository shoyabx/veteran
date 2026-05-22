from app.services.evidence_assembly import assemble_evidence


def test_evidence_ordering_chronological():
    rows = [
        {'rank': 2, 'citation_payload': {'conversation_id': 't1', 'attachment_id': None, 'source_timestamp': '2026-01-02T00:00:00'}},
        {'rank': 1, 'citation_payload': {'conversation_id': 't1', 'attachment_id': None, 'source_timestamp': '2026-01-01T00:00:00'}},
    ]
    ev = assemble_evidence(rows)
    thread = ev['thread_evidence']['t1']
    assert thread[0]['citation_payload']['source_timestamp'] == '2026-01-01T00:00:00'
