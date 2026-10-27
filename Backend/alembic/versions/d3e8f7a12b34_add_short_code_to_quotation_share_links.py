"""add short_code to quotation_share_links

Revision ID: d3e8f7a12b34
Revises: c7f91a2e34d1
Create Date: 2026-10-27 17:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd3e8f7a12b34'
down_revision = 'c7f91a2e34d1'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('quotation_share_links', sa.Column('short_code', sa.String(length=32), nullable=True))
    op.create_index('ix_quotation_share_links_short_code', 'quotation_share_links', ['short_code'], unique=True)
    op.create_index('ix_quotation_share_links_short_lookup', 'quotation_share_links', ['short_code', 'is_revoked'])

def downgrade() -> None:
    op.drop_index('ix_quotation_share_links_short_lookup', table_name='quotation_share_links')
    op.drop_index('ix_quotation_share_links_short_code', table_name='quotation_share_links')
    op.drop_column('quotation_share_links', 'short_code')
