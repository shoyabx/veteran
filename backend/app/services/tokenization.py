from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

try:
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover
    tiktoken = None


class TokenizerError(Exception):
    pass


class Tokenizer(Protocol):
    def encode(self, text: str) -> list[int]: ...
    def decode(self, tokens: list[int]) -> str: ...


@dataclass
class TokenBudget:
    chunk_budget: int
    overlap_budget: int
    reserved_headroom: int


class TiktokenTokenizer:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._fallback = False
        if tiktoken is None:
            self._fallback = True
            self._enc = None
        else:
            try:
                self._enc = tiktoken.encoding_for_model(model_name)
            except Exception:
                self._enc = tiktoken.get_encoding('cl100k_base')

    def encode(self, text: str) -> list[int]:
        if not text:
            return []
        if self._fallback:
            return [abs(hash(x)) % 100000 for x in text.split()]
        return self._enc.encode(text)

    def decode(self, tokens: list[int]) -> str:
        if self._fallback:
            return ' '.join([str(t) for t in tokens])
        return self._enc.decode(tokens)


def compute_budget(max_context_tokens: int, reserved_headroom: int, overlap_ratio: float = 0.15) -> TokenBudget:
    if reserved_headroom >= max_context_tokens:
        raise TokenizerError('reserved_headroom_too_large')
    chunk_budget = max_context_tokens - reserved_headroom
    overlap_budget = max(1, int(chunk_budget * overlap_ratio))
    return TokenBudget(chunk_budget=chunk_budget, overlap_budget=overlap_budget, reserved_headroom=reserved_headroom)
