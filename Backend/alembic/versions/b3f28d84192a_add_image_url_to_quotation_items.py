"""Add image_url to quotation_items

Revision ID: b3f28d84192a
Revises: 17bd8c54278d
Create Date: 2026-10-15 17:28:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b3f28d84192a'
down_revision = '17bd8c54278d'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility while remaining standard for Postgres
    with op.batch_alter_table('quotation_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_url', sa.String(length=512), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('quotation_items', schema=None) as batch_op:
        batch_op.drop_column('image_url')
