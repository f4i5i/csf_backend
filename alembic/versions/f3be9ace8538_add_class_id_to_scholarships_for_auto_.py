"""add_class_id_to_scholarships_for_auto_expiry

Revision ID: f3be9ace8538
Revises: 489564e3886a
Create Date: 2025-11-29 23:08:08.512258

This migration adds class_id to scholarships so they can automatically
expire when the associated class ends. When class_id is set, the scholarship's
valid_until will be computed from the class end_date.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3be9ace8538'
down_revision: Union[str, Sequence[str], None] = '489564e3886a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add class_id to scholarships table."""
    # Add class_id column (optional - scholarship can be general or class-specific)
    op.add_column(
        'scholarships',
        sa.Column('class_id', sa.String(36), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_scholarships_class_id',
        'scholarships',
        'classes',
        ['class_id'],
        ['id']
    )

    # Add index for better query performance
    op.create_index(
        'ix_scholarships_class_id',
        'scholarships',
        ['class_id']
    )


def downgrade() -> None:
    """Remove class_id from scholarships table."""
    op.drop_index('ix_scholarships_class_id', 'scholarships')
    op.drop_constraint('fk_scholarships_class_id', 'scholarships', type_='foreignkey')
    op.drop_column('scholarships', 'class_id')
