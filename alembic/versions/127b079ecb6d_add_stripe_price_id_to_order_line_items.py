"""add_stripe_price_id_to_order_line_items

Revision ID: 127b079ecb6d
Revises: 903a88092269
Create Date: 2025-12-14 05:21:50.008571

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '127b079ecb6d'
down_revision: Union[str, Sequence[str], None] = '903a88092269'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add stripe_price_id column to order_line_items table."""
    op.add_column('order_line_items', sa.Column('stripe_price_id', sa.String(100), nullable=True))
    op.create_index(op.f('ix_order_line_items_stripe_price_id'), 'order_line_items', ['stripe_price_id'], unique=False)


def downgrade() -> None:
    """Remove stripe_price_id column from order_line_items table."""
    op.drop_index(op.f('ix_order_line_items_stripe_price_id'), table_name='order_line_items')
    op.drop_column('order_line_items', 'stripe_price_id')
