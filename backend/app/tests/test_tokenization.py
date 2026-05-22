from app.services.tokenization import TiktokenTokenizer


def test_token_counting_consistent():
    tok = TiktokenTokenizer('text-embedding-3-small')
    text = 'Veteran semantic indexing hardening.'
    a = tok.encode(text)
    b = tok.encode(text)
    assert len(a) == len(b)
    assert tok.decode(a) == tok.decode(b)
