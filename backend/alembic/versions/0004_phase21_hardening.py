"""phase2.1 semantic indexing hardening

Revision ID: 0004_phase21
Revises: 0003_phase2
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004_phase21'
down_revision = '0003_phase2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('embedding_jobs', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))

    op.add_column('indexed_chunks', sa.Column('chunk_checksum', sa.String(length=64), nullable=False, server_default=''))
    op.add_column('indexed_chunks', sa.Column('semantic_version', sa.String(length=16), nullable=False, server_default='2.1'))

    op.add_column('attachment_chunks', sa.Column('chunk_checksum', sa.String(length=64), nullable=False, server_default=''))

    op.add_column('vector_index_states', sa.Column('last_content_hash', sa.String(length=64), nullable=True))

    op.create_table('indexing_metrics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('embedding_jobs.id', ondelete='CASCADE'), nullable=True),
        sa.Column('metric_name', sa.String(length=64), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('correlation_id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_indexing_metrics_tenant_id', 'indexing_metrics', ['tenant_id'])
    op.create_index('ix_indexing_metrics_job_id', 'indexing_metrics', ['job_id'])

    op.create_table('embedding_usage_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('embedding_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('model_name', sa.String(length=128), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_cost_usd_micro', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('batch_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('correlation_id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_embedding_usage_logs_tenant_id', 'embedding_usage_logs', ['tenant_id'])
    op.create_index('ix_embedding_usage_logs_job_id', 'embedding_usage_logs', ['job_id'])

    op.create_table('parser_failures',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('embedding_jobs.id', ondelete='CASCADE'), nullable=True),
        sa.Column('attachment_id', sa.Integer(), sa.ForeignKey('attachments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('mime_type', sa.String(length=128), nullable=True),
        sa.Column('error_code', sa.String(length=64), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('correlation_id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_parser_failures_tenant_id', 'parser_failures', ['tenant_id'])

    op.create_table('worker_heartbeats',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('worker_name', sa.String(length=64), nullable=False),
        sa.Column('worker_instance_id', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.Column('meta_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint('worker_name', 'worker_instance_id', name='uq_worker_instance')
    )
    op.create_index('ix_worker_heartbeats_worker_name', 'worker_heartbeats', ['worker_name'])

    op.create_table('dead_letter_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_type', sa.String(length=64), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reason', sa.String(length=128), nullable=False),
        sa.Column('correlation_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='open'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_dead_letter_jobs_tenant_id', 'dead_letter_jobs', ['tenant_id'])


def downgrade() -> None:
    op.drop_table('dead_letter_jobs')
    op.drop_table('worker_heartbeats')
    op.drop_table('parser_failures')
    op.drop_table('embedding_usage_logs')
    op.drop_table('indexing_metrics')
    op.drop_column('vector_index_states', 'last_content_hash')
    op.drop_column('attachment_chunks', 'chunk_checksum')
    op.drop_column('indexed_chunks', 'semantic_version')
    op.drop_column('indexed_chunks', 'chunk_checksum')
    op.drop_column('embedding_jobs', 'retry_count')
