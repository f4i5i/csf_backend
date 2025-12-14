"""make_enrollment_organization_id_nullable

Revision ID: e4f3830814f2
Revises: 43d88e9f175f
Create Date: 2025-12-14 04:46:36.112467

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f3830814f2'
down_revision: Union[str, Sequence[str], None] = '43d88e9f175f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make organization_id nullable in enrollments table."""
    op.alter_column('enrollments', 'organization_id',
                    existing_type=sa.String(36),
                    nullable=True)


def downgrade() -> None:
    """Make organization_id not nullable in enrollments table."""
    op.alter_column('enrollments', 'organization_id',
                    existing_type=sa.String(36),
                    nullable=False)
