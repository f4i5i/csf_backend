"""make_order_line_items_organization_id_nullable

Revision ID: 903a88092269
Revises: 80efa11c759f
Create Date: 2025-12-14 04:55:23.670393

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '903a88092269'
down_revision: Union[str, Sequence[str], None] = '80efa11c759f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make organization_id nullable in order_line_items table."""
    op.alter_column('order_line_items', 'organization_id',
                    existing_type=sa.String(36),
                    nullable=True)


def downgrade() -> None:
    """Make organization_id not nullable in order_line_items table."""
    op.alter_column('order_line_items', 'organization_id',
                    existing_type=sa.String(36),
                    nullable=False)
