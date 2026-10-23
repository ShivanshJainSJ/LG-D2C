"""create quotation artifacts and sharing tables

Revision ID: c7f91a2e34d1
Revises: b3f28d84192a
Create Date: 2026-10-23 13:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c7f91a2e34d1'
down_revision = 'b3f28d84192a'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. quotation_artifacts
    op.create_table(
        'quotation_artifacts',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('quotation_id', sa.String(length=36), sa.ForeignKey('quotations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('revision_id', sa.String(length=36), sa.ForeignKey('quotation_revisions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('storage_key', sa.String(length=512), nullable=False),
        sa.Column('storage_provider', sa.String(length=50), nullable=False, server_default='local'),
        sa.Column('content_type', sa.String(length=100), nullable=False, server_default='application/pdf'),
        sa.Column('byte_size', sa.Integer(), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('revision_id', name='uq_quotation_artifacts_revision_id')
    )
    op.create_index('ix_quotation_artifacts_quotation_id', 'quotation_artifacts', ['quotation_id'])
    op.create_index('ix_quotation_artifacts_sha256', 'quotation_artifacts', ['sha256_hash'])

    # 2. quotation_share_links
    op.create_table(
        'quotation_share_links',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('quotation_id', sa.String(length=36), sa.ForeignKey('quotations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('revision_id', sa.String(length=36), sa.ForeignKey('quotation_revisions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_by_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_by_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('token_hash', name='uq_quotation_share_links_token_hash')
    )
    op.create_index('ix_quotation_share_links_quotation_id', 'quotation_share_links', ['quotation_id'])
    op.create_index('ix_quotation_share_links_revision_id', 'quotation_share_links', ['revision_id'])
    op.create_index('ix_quotation_share_links_token_hash', 'quotation_share_links', ['token_hash'])
    op.create_index('ix_quotation_share_links_lookup', 'quotation_share_links', ['token_hash', 'is_revoked'])

    # 3. shared_quotation_access
    op.create_table(
        'shared_quotation_access',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('share_link_id', sa.String(length=36), sa.ForeignKey('quotation_share_links.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(length=20), nullable=False),
        sa.Column('ip_hash', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_index('ix_shared_access_link_event', 'shared_quotation_access', ['share_link_id', 'event_type'])
    op.create_index('ix_shared_access_created_at', 'shared_quotation_access', ['created_at'])

def downgrade() -> None:
    op.drop_table('shared_quotation_access')
    op.drop_table('quotation_share_links')
    op.drop_table('quotation_artifacts')
