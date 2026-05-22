from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, Float, UniqueConstraint, Index, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class RetrievalQuery(Base):
    __tablename__ = 'retrieval_queries'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    mailbox_id: Mapped[int] = mapped_column(ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=True, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_query: Mapped[str] = mapped_column(Text, nullable=False)
    query_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    score_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    filter_payload: Mapped[dict] = mapped_column(JSONB, nullable=True)
    query_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='completed')
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RetrievalResult(Base):
    __tablename__ = 'retrieval_results'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    query_id: Mapped[int] = mapped_column(ForeignKey('retrieval_queries.id', ondelete='CASCADE'), nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_id: Mapped[str] = mapped_column(String(128), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(128), nullable=False)
    email_id: Mapped[int] = mapped_column(ForeignKey('emails.id', ondelete='CASCADE'), nullable=False, index=True)
    mailbox_id: Mapped[int] = mapped_column(ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    attachment_id: Mapped[int] = mapped_column(ForeignKey('attachments.id', ondelete='CASCADE'), nullable=True, index=True)
    source_start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    source_end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    vector_score: Mapped[float] = mapped_column(Float, nullable=False)
    rerank_score: Mapped[float] = mapped_column(Float, nullable=False)
    citation_integrity_score: Mapped[float] = mapped_column(Float, nullable=False)
    retrieval_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    citation_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_stale_rejected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'query_id', 'chunk_id', name='uq_result_chunk_per_query'),
        Index('ix_retrieval_results_tenant_query_rank', 'tenant_id', 'query_id', 'rank'),
    )


class CitationValidationFailure(Base):
    __tablename__ = 'citation_validation_failures'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    query_id: Mapped[int] = mapped_column(ForeignKey('retrieval_queries.id', ondelete='CASCADE'), nullable=False, index=True)
    vector_id: Mapped[str] = mapped_column(String(128), nullable=True)
    chunk_id: Mapped[str] = mapped_column(String(128), nullable=True)
    failure_code: Mapped[str] = mapped_column(String(64), nullable=False)
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RerankMetric(Base):
    __tablename__ = 'rerank_metrics'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    query_id: Mapped[int] = mapped_column(ForeignKey('retrieval_queries.id', ondelete='CASCADE'), nullable=False, index=True)
    vector_id: Mapped[str] = mapped_column(String(128), nullable=False)
    semantic_similarity: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_relevance: Mapped[float] = mapped_column(Float, nullable=False)
    recency_weight: Mapped[float] = mapped_column(Float, nullable=False)
    continuity_weight: Mapped[float] = mapped_column(Float, nullable=False)
    attachment_weight: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RetrievalTelemetry(Base):
    __tablename__ = 'retrieval_telemetry'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    query_id: Mapped[int] = mapped_column(ForeignKey('retrieval_queries.id', ondelete='CASCADE'), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    tags: Mapped[dict] = mapped_column(JSONB, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
