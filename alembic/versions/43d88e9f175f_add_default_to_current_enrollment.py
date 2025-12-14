"""add_default_to_current_enrollment

Revision ID: 43d88e9f175f
Revises: fc05062493a0
Create Date: 2025-12-14 03:57:08.716597

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43d88e9f175f'
down_revision: Union[str, Sequence[str], None] = 'fc05062493a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add database-level default value of 0 to current_enrollment column."""
    # Set default value to 0 for current_enrollment
    op.alter_column('classes', 'current_enrollment',
               existing_type=sa.Integer(),
               server_default='0',
               nullable=False)


def downgrade() -> None:
    """Remove database-level default from current_enrollment column."""
    # Remove default value
    op.alter_column('classes', 'current_enrollment',
               existing_type=sa.Integer(),
               server_default=None,
               nullable=False)
