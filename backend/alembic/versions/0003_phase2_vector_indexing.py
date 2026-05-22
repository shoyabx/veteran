"""phase2 embedding and vector indexing foundation

Revision ID: 0003_phase2
Revises: 0002_phase1b
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003_phase2'
down_revision = '0002_phase1b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('embedding_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mailbox_id', sa.Integer(), sa.ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email_id', sa.Integer(), sa.ForeignKey('emails.id', ondelete='CASCADE'), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('model_name', sa.String(length=128), nullable=False),
        sa.Column('correlation_id', sa.String(length=64), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_embedding_jobs_tenant_id', 'embedding_jobs', ['tenant_id'])
    op.create_index('ix_embedding_jobs_mailbox_id', 'embedding_jobs', ['mailbox_id'])
    op.create_index('ix_embedding_jobs_email_id', 'embedding_jobs', ['email_id'])
    op.create_index('ix_embedding_jobs_status', 'embedding_jobs', ['status'])

    op.create_table('embedding_failures',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('embedding_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_id', sa.String(length=128), nullable=True),
        sa.Column('stage', sa.String(length=64), nullable=False),
        sa.Column('error_code', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('retryable', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_embedding_failures_tenant_id', 'embedding_failures', ['tenant_id'])
    op.create_index('ix_embedding_failures_job_id', 'embedding_failures', ['job_id'])

    op.create_table('indexed_chunks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mailbox_id', sa.Integer(), sa.ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email_id', sa.Integer(), sa.ForeignKey('emails.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attachment_id', sa.Integer(), sa.ForeignKey('attachments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('conversation_id', sa.String(length=255), nullable=True),
        sa.Column('chunk_id', sa.String(length=128), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('source_start_offset', sa.Integer(), nullable=False),
        sa.Column('source_end_offset', sa.Integer(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('source_timestamp', sa.DateTime(), nullable=True),
        sa.Column('vector_id', sa.String(length=128), nullable=False),
        sa.Column('content_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'chunk_id', name='uq_chunk_per_tenant')
    )
    op.create_index('ix_indexed_chunks_tenant_id', 'indexed_chunks', ['tenant_id'])
    op.create_index('ix_indexed_chunks_user_id', 'indexed_chunks', ['user_id'])
    op.create_index('ix_indexed_chunks_mailbox_id', 'indexed_chunks', ['mailbox_id'])
    op.create_index('ix_indexed_chunks_email_id', 'indexed_chunks', ['email_id'])
    op.create_index('ix_indexed_chunks_attachment_id', 'indexed_chunks', ['attachment_id'])
    op.create_index('ix_indexed_chunks_conversation_id', 'indexed_chunks', ['conversation_id'])
    op.create_index('ix_indexed_chunks_tenant_email', 'indexed_chunks', ['tenant_id', 'email_id'])

    op.create_table('vector_index_states',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mailbox_id', sa.Integer(), sa.ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('last_indexed_email_id', sa.Integer(), nullable=True),
        sa.Column('last_indexed_at', sa.DateTime(), nullable=True),
        sa.Column('checkpoint_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'mailbox_id', name='uq_vector_state_tenant_mailbox')
    )
    op.create_index('ix_vector_index_states_tenant_id', 'vector_index_states', ['tenant_id'])
    op.create_index('ix_vector_index_states_mailbox_id', 'vector_index_states', ['mailbox_id'])

    op.create_table('attachment_chunks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attachment_id', sa.Integer(), sa.ForeignKey('attachments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_id', sa.String(length=128), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('source_start_offset', sa.Integer(), nullable=False),
        sa.Column('source_end_offset', sa.Integer(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'attachment_id', 'chunk_id', name='uq_attachment_chunk_per_tenant')
    )
    op.create_index('ix_attachment_chunks_tenant_id', 'attachment_chunks', ['tenant_id'])
    op.create_index('ix_attachment_chunks_attachment_id', 'attachment_chunks', ['attachment_id'])


def downgrade() -> None:
    op.drop_table('attachment_chunks')
    op.drop_table('vector_index_states')
    op.drop_table('indexed_chunks')
    op.drop_table('embedding_failures')
    op.drop_table('embedding_jobs')
