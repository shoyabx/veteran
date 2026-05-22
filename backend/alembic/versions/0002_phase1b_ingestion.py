"""phase1b ingestion foundation

Revision ID: 0002_phase1b
Revises: 0001_phase1a
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002_phase1b'
down_revision = '0001_phase1a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('mailboxes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('provider_mailbox_id', sa.String(length=255), nullable=False),
        sa.Column('email_address', sa.String(length=320), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'provider', 'provider_mailbox_id', name='uq_mailbox_provider_per_tenant'),
    )
    op.create_index('ix_mailboxes_tenant_id', 'mailboxes', ['tenant_id'])
    op.create_index('ix_mailboxes_user_id', 'mailboxes', ['user_id'])

    op.create_table('sync_states',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mailbox_id', sa.Integer(), sa.ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('delta_token', sa.Text(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('mailbox_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('mailbox_id')
    )
    op.create_index('ix_sync_states_tenant_id', 'sync_states', ['tenant_id'])

    op.create_table('emails',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mailbox_id', sa.Integer(), sa.ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('graph_message_id', sa.String(length=255), nullable=False),
        sa.Column('internet_message_id', sa.String(length=512), nullable=True),
        sa.Column('conversation_id', sa.String(length=255), nullable=True),
        sa.Column('subject', sa.Text(), nullable=True),
        sa.Column('sender_email', sa.String(length=320), nullable=True),
        sa.Column('sender_name', sa.String(length=255), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=True),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('importance', sa.String(length=32), nullable=True),
        sa.Column('categories', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('has_attachments', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('in_reply_to', sa.String(length=512), nullable=True),
        sa.Column('references_header', sa.Text(), nullable=True),
        sa.Column('parent_message_id', sa.String(length=255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('raw_etag', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'mailbox_id', 'graph_message_id', name='uq_email_graph_id_per_mailbox')
    )
    op.create_index('ix_emails_tenant_id', 'emails', ['tenant_id'])
    op.create_index('ix_emails_mailbox_id', 'emails', ['mailbox_id'])
    op.create_index('ix_emails_conversation_id', 'emails', ['conversation_id'])
    op.create_index('ix_emails_sent_at', 'emails', ['sent_at'])
    op.create_index('ix_emails_received_at', 'emails', ['received_at'])
    op.create_index('ix_emails_tenant_mailbox_received', 'emails', ['tenant_id','mailbox_id','received_at'])

    op.create_table('email_participants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email_id', sa.Integer(), sa.ForeignKey('emails.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
    )
    op.create_index('ix_email_participants_tenant_id', 'email_participants', ['tenant_id'])
    op.create_index('ix_email_participants_email_id', 'email_participants', ['email_id'])

    op.create_table('attachments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email_id', sa.Integer(), sa.ForeignKey('emails.id', ondelete='CASCADE'), nullable=False),
        sa.Column('graph_attachment_id', sa.String(length=255), nullable=False),
        sa.Column('file_name', sa.String(length=512), nullable=False),
        sa.Column('content_type', sa.String(length=128), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=True),
        sa.Column('is_supported_type', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'email_id', 'graph_attachment_id', name='uq_attachment_graph_per_email')
    )
    op.create_index('ix_attachments_tenant_id', 'attachments', ['tenant_id'])
    op.create_index('ix_attachments_email_id', 'attachments', ['email_id'])

    op.create_table('attachment_storage_refs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attachment_id', sa.Integer(), sa.ForeignKey('attachments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('storage_provider', sa.String(length=64), nullable=False),
        sa.Column('storage_key', sa.String(length=1024), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('attachment_id')
    )
    op.create_index('ix_attachment_storage_refs_tenant_id', 'attachment_storage_refs', ['tenant_id'])

    op.create_table('ingestion_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mailbox_id', sa.Integer(), sa.ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('job_type', sa.String(length=32), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('correlation_id', sa.String(length=64), nullable=False),
    )
    op.create_index('ix_ingestion_jobs_tenant_id', 'ingestion_jobs', ['tenant_id'])
    op.create_index('ix_ingestion_jobs_mailbox_id', 'ingestion_jobs', ['mailbox_id'])
    op.create_index('ix_ingestion_jobs_status', 'ingestion_jobs', ['status'])

    op.create_table('ingestion_failures',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('ingestion_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stage', sa.String(length=64), nullable=False),
        sa.Column('error_code', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('retryable', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_ingestion_failures_tenant_id', 'ingestion_failures', ['tenant_id'])
    op.create_index('ix_ingestion_failures_job_id', 'ingestion_failures', ['job_id'])


def downgrade() -> None:
    op.drop_table('ingestion_failures')
    op.drop_table('ingestion_jobs')
    op.drop_table('attachment_storage_refs')
    op.drop_table('attachments')
    op.drop_table('email_participants')
    op.drop_table('emails')
    op.drop_table('sync_states')
    op.drop_table('mailboxes')
