"""add_has_medical_alert_to_children

Revision ID: 489564e3886a
Revises: ada926e19a3d
Create Date: 2025-11-29 22:57:22.146068

This migration adds a has_medical_alert boolean field to show a visual indicator
for children with medical conditions on check-in/attendance dashboards without
exposing the actual medical information.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '489564e3886a'
down_revision: Union[str, Sequence[str], None] = 'ada926e19a3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add has_medical_alert field to children table."""
    # Add has_medical_alert column
    op.add_column(
        'children',
        sa.Column('has_medical_alert', sa.Boolean(), nullable=False, server_default='false')
    )

    # Update existing records: set to true if medical_conditions_encrypted is not null
    op.execute("""
        UPDATE children
        SET has_medical_alert = true
        WHERE medical_conditions_encrypted IS NOT NULL
          AND medical_conditions_encrypted != ''
          AND has_no_medical_conditions = false
    """)


def downgrade() -> None:
    """Remove has_medical_alert field from children table."""
    op.drop_column('children', 'has_medical_alert')
