from __future__ import annotations
import hashlib
from dataclasses import dataclass

from app.services.tokenization import TiktokenTokenizer, compute_budget

CHUNK_SCHEMA_VERSION = '2.1'


@dataclass
class Chunk:
    chunk_id: str
    text: str
    start_offset: int
    end_offset: int
    token_count: int
    checksum: str
    content_version: int


class DeterministicChunker:
    def __init__(self, model_name: str = 'text-embedding-3-small', max_context_tokens: int = 8192, reserved_headroom: int = 1024):
        self.tokenizer = TiktokenTokenizer(model_name)
        self.budget = compute_budget(max_context_tokens=max_context_tokens, reserved_headroom=reserved_headroom)

    def chunk_text(self, text: str, lineage_key: str) -> list[Chunk]:
        tokens = self.tokenizer.encode(text)
        if not tokens:
            return []
        chunks: list[Chunk] = []
        i = 0
        max_tokens = self.budget.chunk_budget
        overlap = min(self.budget.overlap_budget, max_tokens // 2)

        while i < len(tokens):
            j = min(i + max_tokens, len(tokens))
            slice_tokens = tokens[i:j]
            if len(slice_tokens) > max_tokens:
                raise ValueError('chunk_token_overflow')
            chunk_text = self.tokenizer.decode(slice_tokens)
            checksum = hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()
            raw = f'{CHUNK_SCHEMA_VERSION}:{lineage_key}:{i}:{j}:{checksum}'.encode('utf-8')
            chunk_id = hashlib.sha256(raw).hexdigest()[:32]
            chunks.append(Chunk(
                chunk_id=chunk_id,
                text=chunk_text,
                start_offset=i,
                end_offset=j,
                token_count=len(slice_tokens),
                checksum=checksum,
                content_version=1,
            ))
            if j >= len(tokens):
                break
            next_i = j - overlap
            if next_i <= i:
                next_i = i + 1
            i = next_i

        for idx in range(1, len(chunks)):
            prev = chunks[idx - 1]
            cur = chunks[idx]
            expected = prev.end_offset - overlap
            if cur.start_offset != expected:
                raise ValueError('overlap_consistency_validation_failed')
        return chunks
