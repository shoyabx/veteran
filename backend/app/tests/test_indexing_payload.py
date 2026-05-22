from app.services.chunking import DeterministicChunker


def test_lineage_fields_present():
    c = DeterministicChunker(model_name='text-embedding-3-small', max_context_tokens=64, reserved_headroom=16)
    chunks = c.chunk_text('a b c d e f g h i j k l', lineage_key='email:1:2')
    assert chunks[0].chunk_id
    assert chunks[0].start_offset == 0
    assert chunks[0].end_offset > chunks[0].start_offset
    assert chunks[0].checksum
    assert chunks[0].content_version == 1
