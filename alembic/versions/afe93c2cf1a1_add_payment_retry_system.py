"""add_payment_retry_system

Revision ID: afe93c2cf1a1
Revises: 2d6dff52eee4
Create Date: 2025-11-30 01:23:35.152170

Adds payment retry system with 3 automatic retry attempts:
- Retry count tracking
- Scheduled retry times
- Email notifications on each failure
- Admin notification after final failure
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'afe93c2cf1a1'
down_revision: Union[str, Sequence[str], None] = '2d6dff52eee4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add payment retry fields."""
    # Add retry_count field
    op.add_column(
        'payments',
        sa.Column(
            'retry_count',
            sa.Integer,
            nullable=False,
            server_default='0'
        )
    )

    # Add next_retry_at field for scheduled retries
    op.add_column(
        'payments',
        sa.Column(
            'next_retry_at',
            sa.DateTime(timezone=True),
            nullable=True
        )
    )

    # Add last_retry_at field to track when last retry occurred
    op.add_column(
        'payments',
        sa.Column(
            'last_retry_at',
            sa.DateTime(timezone=True),
            nullable=True
        )
    )

    # Add index on next_retry_at for efficient querying of pending retries
    op.create_index(
        'ix_payments_next_retry_at',
        'payments',
        ['next_retry_at']
    )


def downgrade() -> None:
    """Remove payment retry fields."""
    op.drop_index('ix_payments_next_retry_at', 'payments')
    op.drop_column('payments', 'last_retry_at')
    op.drop_column('payments', 'next_retry_at')
    op.drop_column('payments', 'retry_count')
