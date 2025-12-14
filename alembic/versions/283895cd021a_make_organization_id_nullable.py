"""make_organization_id_nullable

Revision ID: 283895cd021a
Revises: 32af0f6f3f05
Create Date: 2025-12-14 03:06:39.214520

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '283895cd021a'
down_revision: Union[str, Sequence[str], None] = '32af0f6f3f05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make organization_id nullable in classes table."""
    op.alter_column('classes', 'organization_id',
               existing_type=sa.VARCHAR(),
               nullable=True)


def downgrade() -> None:
    """Revert organization_id to NOT NULL."""
    op.alter_column('classes', 'organization_id',
               existing_type=sa.VARCHAR(),
               nullable=False)
