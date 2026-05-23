"""phase5 conversational synthesis persistence

Revision ID: 0006_phase5
Revises: 0005_phase3
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = '0006_phase5'
down_revision = '0005_phase3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new synthesis & calibration columns to retrieval_queries
    op.add_column('retrieval_queries', sa.Column('answer', sa.Text(), nullable=True))
    op.add_column('retrieval_queries', sa.Column('evidence_snapshot_hash', sa.String(length=64), nullable=True))
    op.add_column('retrieval_queries', sa.Column('retrieval_version', sa.Integer(), nullable=True, server_default=sa.text('1')))
    op.add_column('retrieval_queries', sa.Column('synthesis_version', sa.Integer(), nullable=True, server_default=sa.text('1')))
    op.add_column('retrieval_queries', sa.Column('citation_checksum', sa.String(length=64), nullable=True))
    op.add_column('retrieval_queries', sa.Column('vector_index_version', sa.String(length=32), nullable=True))
    op.add_column('retrieval_queries', sa.Column('unsupported_claim_risk', sa.Float(), nullable=True))
    op.add_column('retrieval_queries', sa.Column('retrieval_coverage_score', sa.Float(), nullable=True))
    op.add_column('retrieval_queries', sa.Column('synthesis_validation_status', sa.String(length=32), nullable=True))


def downgrade() -> None:
    # Drop synthesis columns from retrieval_queries
    op.drop_column('retrieval_queries', 'synthesis_validation_status')
    op.drop_column('retrieval_queries', 'retrieval_coverage_score')
    op.drop_column('retrieval_queries', 'unsupported_claim_risk')
    op.drop_column('retrieval_queries', 'vector_index_version')
    op.drop_column('retrieval_queries', 'citation_checksum')
    op.drop_column('retrieval_queries', 'synthesis_version')
    op.drop_column('retrieval_queries', 'retrieval_version')
    op.drop_column('retrieval_queries', 'evidence_snapshot_hash')
    op.drop_column('retrieval_queries', 'answer')
