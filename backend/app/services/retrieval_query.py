from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.services.tokenization import TiktokenTokenizer


@dataclass
class NormalizedQuery:
    raw_query: str
    normalized_query: str
    query_checksum: str
    query_tokens: int


def normalize_query(query: str, model_name: str) -> NormalizedQuery:
    cleaned = re.sub(r'\s+', ' ', (query or '').strip().lower())
    if not cleaned:
        raise ValueError('empty_query_not_allowed')
    tokenizer = TiktokenTokenizer(model_name)
    tokens = tokenizer.encode(cleaned)
    if len(tokens) == 0:
        raise ValueError('empty_query_tokens_not_allowed')
    checksum = hashlib.sha256(cleaned.encode('utf-8')).hexdigest()
    return NormalizedQuery(raw_query=query, normalized_query=cleaned, query_checksum=checksum, query_tokens=len(tokens))
