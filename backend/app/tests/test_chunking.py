from app.services.chunking import DeterministicChunker


def test_chunking_is_deterministic():
    text = ' '.join(['token'] * 2000)
    c = DeterministicChunker(model_name='text-embedding-3-small', max_context_tokens=512, reserved_headroom=128)
    a = c.chunk_text(text, lineage_key='k1')
    b = c.chunk_text(text, lineage_key='k1')
    assert [x.chunk_id for x in a] == [x.chunk_id for x in b]


def test_chunk_overlap_and_bounds():
    text = ' '.join([str(i) for i in range(1000)])
    c = DeterministicChunker(model_name='text-embedding-3-small', max_context_tokens=300, reserved_headroom=100)
    out = c.chunk_text(text, lineage_key='k2')
    assert len(out) > 1
    for i in range(1, len(out)):
        assert out[i].start_offset < out[i].end_offset
        assert out[i-1].end_offset > out[i].start_offset


def test_checksum_stable():
    c = DeterministicChunker(max_context_tokens=256, reserved_headroom=64)
    chunks = c.chunk_text('alpha beta gamma delta', lineage_key='k3')
    assert chunks[0].checksum
    assert len(chunks[0].checksum) == 64
