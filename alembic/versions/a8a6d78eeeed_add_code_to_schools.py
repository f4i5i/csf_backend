"""add_code_to_schools

Revision ID: a8a6d78eeeed
Revises: 283895cd021a
Create Date: 2025-12-14 03:22:47.577232

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8a6d78eeeed'
down_revision: Union[str, Sequence[str], None] = '283895cd021a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add code column to schools table."""
    op.add_column('schools', sa.Column('code', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Remove code column from schools table."""
    op.drop_column('schools', 'code')
