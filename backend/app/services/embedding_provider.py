from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
import asyncio
import time

from openai import OpenAI


class EmbeddingProviderError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False):
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


@dataclass
class EmbeddingResult:
    vectors: list[list[float]]
    token_usage: int
    latency_ms: int


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str], model_name: str) -> EmbeddingResult:
        ...


class OpenAIEmbeddingProvider:
    def __init__(self, api_key: str, batch_size: int = 64):
        self.client = OpenAI(api_key=api_key)
        self.batch_size = batch_size

    async def embed(self, texts: list[str], model_name: str) -> EmbeddingResult:
        retries = 3
        delay = 1.0
        started = time.perf_counter()
        vectors: list[list[float]] = []
        total_usage = 0
        batches = [texts[i:i+self.batch_size] for i in range(0, len(texts), self.batch_size)]
        for batch in batches:
            for attempt in range(1, retries + 1):
                try:
                    resp = await asyncio.to_thread(self.client.embeddings.create, model=model_name, input=batch)
                    vectors.extend([d.embedding for d in resp.data])
                    usage = getattr(resp, 'usage', None)
                    total_usage += int(getattr(usage, 'total_tokens', 0) or 0)
                    break
                except Exception as e:
                    if attempt == retries:
                        raise EmbeddingProviderError('openai_embed_failed', str(e), retryable=True)
                    await asyncio.sleep(delay)
                    delay *= 2
        latency_ms = int((time.perf_counter() - started) * 1000)
        return EmbeddingResult(vectors=vectors, token_usage=total_usage, latency_ms=latency_ms)
