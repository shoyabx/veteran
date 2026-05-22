from __future__ import annotations


REQUIRED_CITATION_FIELDS = [
    'tenant_id', 'mailbox_id', 'email_id', 'conversation_id', 'chunk_id',
    'source_start_offset', 'source_end_offset', 'source_timestamp', 'content_version', 'semantic_version'
]


def validate_citation_payload(payload: dict) -> tuple[bool, str | None]:
    for key in REQUIRED_CITATION_FIELDS:
        if payload.get(key) is None:
            return False, f'missing_{key}'
    if payload.get('source_start_offset', 0) >= payload.get('source_end_offset', 0):
        return False, 'invalid_source_offsets'
    if payload.get('content_version', 0) < 1:
        return False, 'invalid_content_version'
    return True, None
