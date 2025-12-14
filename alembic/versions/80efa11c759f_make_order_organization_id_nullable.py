"""make_order_organization_id_nullable

Revision ID: 80efa11c759f
Revises: e4f3830814f2
Create Date: 2025-12-14 04:48:08.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80efa11c759f'
down_revision: Union[str, Sequence[str], None] = 'e4f3830814f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make organization_id nullable in orders table."""
    op.alter_column('orders', 'organization_id',
                    existing_type=sa.String(36),
                    nullable=True)


def downgrade() -> None:
    """Make organization_id not nullable in orders table."""
    op.alter_column('orders', 'organization_id',
                    existing_type=sa.String(36),
                    nullable=False)
