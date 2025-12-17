"""add payment_options to classes

Revision ID: payment_options_001
Revises: 127b079ecb6d
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'payment_options_001'
down_revision: Union[str, None] = '127b079ecb6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add payment_options column to classes table
    op.add_column('classes', sa.Column('payment_options', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove payment_options column from classes table
    op.drop_column('classes', 'payment_options')
