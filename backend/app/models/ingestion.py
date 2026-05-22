from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Boolean, Text, BigInteger, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Mailbox(Base):
    __tablename__ = 'mailboxes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default='microsoft_graph')
    provider_mailbox_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email_address: Mapped[str] = mapped_column(String(320), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint('tenant_id', 'provider', 'provider_mailbox_id', name='uq_mailbox_provider_per_tenant'),)

class SyncState(Base):
    __tablename__ = 'sync_states'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    mailbox_id: Mapped[int] = mapped_column(ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False, unique=True)
    delta_token: Mapped[str] = mapped_column(Text, nullable=True)
    last_sync_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    mailbox_state: Mapped[dict] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class Email(Base):
    __tablename__ = 'emails'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    mailbox_id: Mapped[int] = mapped_column(ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False, index=True)
    graph_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    internet_message_id: Mapped[str] = mapped_column(String(512), nullable=True)
    conversation_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(Text, nullable=True)
    sender_email: Mapped[str] = mapped_column(String(320), nullable=True)
    sender_name: Mapped[str] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    body_text: Mapped[str] = mapped_column(Text, nullable=True)
    body_html: Mapped[str] = mapped_column(Text, nullable=True)
    importance: Mapped[str] = mapped_column(String(32), nullable=True)
    categories: Mapped[list] = mapped_column(JSONB, nullable=True)
    has_attachments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    in_reply_to: Mapped[str] = mapped_column(String(512), nullable=True)
    references_header: Mapped[str] = mapped_column(Text, nullable=True)
    parent_message_id: Mapped[str] = mapped_column(String(255), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_etag: Mapped[str] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'mailbox_id', 'graph_message_id', name='uq_email_graph_id_per_mailbox'),
        Index('ix_emails_tenant_mailbox_received', 'tenant_id', 'mailbox_id', 'received_at'),
    )

class EmailParticipant(Base):
    __tablename__ = 'email_participants'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    email_id: Mapped[int] = mapped_column(ForeignKey('emails.id', ondelete='CASCADE'), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # to/cc/bcc
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=True)

class Attachment(Base):
    __tablename__ = 'attachments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    email_id: Mapped[int] = mapped_column(ForeignKey('emails.id', ondelete='CASCADE'), nullable=False, index=True)
    graph_attachment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    is_supported_type: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint('tenant_id', 'email_id', 'graph_attachment_id', name='uq_attachment_graph_per_email'),)

class AttachmentStorageRef(Base):
    __tablename__ = 'attachment_storage_refs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    attachment_id: Mapped[int] = mapped_column(ForeignKey('attachments.id', ondelete='CASCADE'), nullable=False, unique=True)
    storage_provider: Mapped[str] = mapped_column(String(64), nullable=False, default='local')
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class IngestionJob(Base):
    __tablename__ = 'ingestion_jobs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    mailbox_id: Mapped[int] = mapped_column(ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False, default='delta_sync')
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)

class IngestionFailure(Base):
    __tablename__ = 'ingestion_failures'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('ingestion_jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    error_code: Mapped[str] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
