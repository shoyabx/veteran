"""phase3 retrieval + citation validation engine

Revision ID: 0005_phase3
Revises: 0004_phase21
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0005_phase3'
down_revision = '0004_phase21'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('retrieval_queries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mailbox_id', sa.Integer(), sa.ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=True),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('normalized_query', sa.Text(), nullable=False),
        sa.Column('query_checksum', sa.String(length=64), nullable=False),
        sa.Column('top_k', sa.Integer(), nullable=False),
        sa.Column('score_threshold', sa.Float(), nullable=False),
        sa.Column('filter_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('query_tokens', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('correlation_id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_retrieval_queries_tenant_id', 'retrieval_queries', ['tenant_id'])
    op.create_index('ix_retrieval_queries_mailbox_id', 'retrieval_queries', ['mailbox_id'])

    op.create_table('retrieval_results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('query_id', sa.Integer(), sa.ForeignKey('retrieval_queries.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('vector_id', sa.String(length=128), nullable=False),
        sa.Column('chunk_id', sa.String(length=128), nullable=False),
        sa.Column('email_id', sa.Integer(), sa.ForeignKey('emails.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mailbox_id', sa.Integer(), sa.ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', sa.String(length=255), nullable=True),
        sa.Column('attachment_id', sa.Integer(), sa.ForeignKey('attachments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('source_start_offset', sa.Integer(), nullable=False),
        sa.Column('source_end_offset', sa.Integer(), nullable=False),
        sa.Column('source_timestamp', sa.DateTime(), nullable=True),
        sa.Column('vector_score', sa.Float(), nullable=False),
        sa.Column('rerank_score', sa.Float(), nullable=False),
        sa.Column('citation_integrity_score', sa.Float(), nullable=False),
        sa.Column('retrieval_confidence', sa.Float(), nullable=False),
        sa.Column('evidence_confidence', sa.Float(), nullable=False),
        sa.Column('citation_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_stale_rejected', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'query_id', 'chunk_id', name='uq_result_chunk_per_query')
    )
    op.create_index('ix_retrieval_results_tenant_id', 'retrieval_results', ['tenant_id'])
    op.create_index('ix_retrieval_results_query_id', 'retrieval_results', ['query_id'])
    op.create_index('ix_retrieval_results_tenant_query_rank', 'retrieval_results', ['tenant_id', 'query_id', 'rank'])

    op.create_table('citation_validation_failures',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('query_id', sa.Integer(), sa.ForeignKey('retrieval_queries.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vector_id', sa.String(length=128), nullable=True),
        sa.Column('chunk_id', sa.String(length=128), nullable=True),
        sa.Column('failure_code', sa.String(length=64), nullable=False),
        sa.Column('failure_reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_citation_validation_failures_tenant_id', 'citation_validation_failures', ['tenant_id'])
    op.create_index('ix_citation_validation_failures_query_id', 'citation_validation_failures', ['query_id'])

    op.create_table('rerank_metrics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('query_id', sa.Integer(), sa.ForeignKey('retrieval_queries.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vector_id', sa.String(length=128), nullable=False),
        sa.Column('semantic_similarity', sa.Float(), nullable=False),
        sa.Column('metadata_relevance', sa.Float(), nullable=False),
        sa.Column('recency_weight', sa.Float(), nullable=False),
        sa.Column('continuity_weight', sa.Float(), nullable=False),
        sa.Column('attachment_weight', sa.Float(), nullable=False),
        sa.Column('final_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_rerank_metrics_tenant_id', 'rerank_metrics', ['tenant_id'])
    op.create_index('ix_rerank_metrics_query_id', 'rerank_metrics', ['query_id'])

    op.create_table('retrieval_telemetry',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('query_id', sa.Integer(), sa.ForeignKey('retrieval_queries.id', ondelete='CASCADE'), nullable=False),
        sa.Column('metric_name', sa.String(length=64), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('correlation_id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_retrieval_telemetry_tenant_id', 'retrieval_telemetry', ['tenant_id'])
    op.create_index('ix_retrieval_telemetry_query_id', 'retrieval_telemetry', ['query_id'])


def downgrade() -> None:
    op.drop_table('retrieval_telemetry')
    op.drop_table('rerank_metrics')
    op.drop_table('citation_validation_failures')
    op.drop_table('retrieval_results')
    op.drop_table('retrieval_queries')
