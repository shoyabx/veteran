from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Boolean, Text, UniqueConstraint, Index, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class EmbeddingJob(Base):
    __tablename__ = 'embedding_jobs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    mailbox_id: Mapped[int] = mapped_column(ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False, index=True)
    email_id: Mapped[int] = mapped_column(ForeignKey('emails.id', ondelete='CASCADE'), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default='openai')
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

class EmbeddingFailure(Base):
    __tablename__ = 'embedding_failures'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('embedding_jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    chunk_id: Mapped[str] = mapped_column(String(128), nullable=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    error_code: Mapped[str] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class IndexedChunk(Base):
    __tablename__ = 'indexed_chunks'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    mailbox_id: Mapped[int] = mapped_column(ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False, index=True)
    email_id: Mapped[int] = mapped_column(ForeignKey('emails.id', ondelete='CASCADE'), nullable=False, index=True)
    attachment_id: Mapped[int] = mapped_column(ForeignKey('attachments.id', ondelete='CASCADE'), nullable=True, index=True)
    conversation_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    chunk_id: Mapped[str] = mapped_column(String(128), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_checksum: Mapped[str] = mapped_column(String(64), nullable=False, default='')
    source_start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    source_end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    vector_id: Mapped[str] = mapped_column(String(128), nullable=False)
    semantic_version: Mapped[str] = mapped_column(String(16), nullable=False, default='2.1')
    content_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'chunk_id', name='uq_chunk_per_tenant'),
        Index('ix_indexed_chunks_tenant_email', 'tenant_id', 'email_id'),
    )

class VectorIndexState(Base):
    __tablename__ = 'vector_index_states'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    mailbox_id: Mapped[int] = mapped_column(ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False, index=True)
    last_indexed_email_id: Mapped[int] = mapped_column(Integer, nullable=True)
    last_indexed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_content_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    checkpoint_payload: Mapped[dict] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint('tenant_id', 'mailbox_id', name='uq_vector_state_tenant_mailbox'),)

class AttachmentChunk(Base):
    __tablename__ = 'attachment_chunks'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    attachment_id: Mapped[int] = mapped_column(ForeignKey('attachments.id', ondelete='CASCADE'), nullable=False, index=True)
    chunk_id: Mapped[str] = mapped_column(String(128), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_checksum: Mapped[str] = mapped_column(String(64), nullable=False, default='')
    source_start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    source_end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint('tenant_id', 'attachment_id', 'chunk_id', name='uq_attachment_chunk_per_tenant'),)

class IndexingMetric(Base):
    __tablename__ = 'indexing_metrics'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('embedding_jobs.id', ondelete='CASCADE'), nullable=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_value: Mapped[float] = mapped_column(nullable=False)
    tags: Mapped[dict] = mapped_column(JSONB, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class EmbeddingUsageLog(Base):
    __tablename__ = 'embedding_usage_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('embedding_jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd_micro: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    batch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class ParserFailure(Base):
    __tablename__ = 'parser_failures'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('embedding_jobs.id', ondelete='CASCADE'), nullable=True, index=True)
    attachment_id: Mapped[int] = mapped_column(ForeignKey('attachments.id', ondelete='CASCADE'), nullable=True, index=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=True)
    error_code: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class WorkerHeartbeat(Base):
    __tablename__ = 'worker_heartbeats'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True, index=True)
    worker_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    worker_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    meta_payload: Mapped[dict] = mapped_column(JSONB, nullable=True)

    __table_args__ = (UniqueConstraint('worker_name', 'worker_instance_id', name='uq_worker_instance'),)

class DeadLetterJob(Base):
    __tablename__ = 'dead_letter_jobs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(String(128), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='open')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
