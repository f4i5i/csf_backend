"""add_new_class_fields_registration_recurrence_links

Revision ID: d4f6348fa314
Revises: 1998a6839162
Create Date: 2025-12-14 01:43:48.698429

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f6348fa314'
down_revision: Union[str, Sequence[str], None] = '1998a6839162'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns
    op.add_column('classes', sa.Column('school_code', sa.String(length=50), nullable=True))
    op.add_column('classes', sa.Column('website_link', sa.String(length=500), nullable=True))
    op.add_column('classes', sa.Column('area_id', sa.String(length=36), nullable=True))
    op.add_column('classes', sa.Column('coach_id', sa.String(length=36), nullable=True))
    op.add_column('classes', sa.Column('registration_start_date', sa.Date(), nullable=True))
    op.add_column('classes', sa.Column('registration_end_date', sa.Date(), nullable=True))
    op.add_column('classes', sa.Column('recurrence_pattern', sa.String(length=20), nullable=True))
    op.add_column('classes', sa.Column('repeat_every_weeks', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_classes_area_id'), 'classes', ['area_id'], unique=False)
    op.create_index(op.f('ix_classes_coach_id'), 'classes', ['coach_id'], unique=False)

    # Add 'one-time' value to ClassType enum
    op.execute("ALTER TYPE classtype ADD VALUE IF NOT EXISTS 'one-time'")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop columns
    op.drop_index(op.f('ix_classes_coach_id'), table_name='classes')
    op.drop_index(op.f('ix_classes_area_id'), table_name='classes')
    op.drop_column('classes', 'repeat_every_weeks')
    op.drop_column('classes', 'recurrence_pattern')
    op.drop_column('classes', 'registration_end_date')
    op.drop_column('classes', 'registration_start_date')
    op.drop_column('classes', 'coach_id')
    op.drop_column('classes', 'area_id')
    op.drop_column('classes', 'website_link')
    op.drop_column('classes', 'school_code')

    # Note: Cannot remove enum value in PostgreSQL without recreating the type
    # If you need to remove 'one-time' value, you'll need to manually recreate the enum
