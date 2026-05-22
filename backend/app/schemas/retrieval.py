from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Any


class RetrievalQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)
    score_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    filters: dict[str, Any] | None = None


class RetrievalQueryResponse(BaseModel):
    query_id: int
    status: str


class RetrievalResultItem(BaseModel):
    rank: int
    vector_id: str
    chunk_id: str
    email_id: int
    mailbox_id: int
    conversation_id: Optional[str]
    attachment_id: Optional[int]
    vector_score: float
    rerank_score: float
    retrieval_confidence: float
    evidence_confidence: float
    citation_integrity_score: float
    citation_payload: dict


class RetrievalQueryStatusResponse(BaseModel):
    query_id: int
    status: str
    created_at: datetime
    results: list[RetrievalResultItem]


class RetrievalEvidenceResponse(BaseModel):
    query_id: int
    evidence: dict
