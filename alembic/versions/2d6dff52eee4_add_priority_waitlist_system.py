"""add_priority_waitlist_system

Revision ID: 2d6dff52eee4
Revises: 462b747b9f1d
Create Date: 2025-11-30 00:52:05.980444

Adds 2-tier priority waitlist system:
- Priority: Auto-charge and promote when spot opens (requires CC on file)
- Regular: 12-hour claim window with manual payment
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d6dff52eee4'
down_revision: Union[str, Sequence[str], None] = '462b747b9f1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add priority waitlist fields to enrollments."""
    # Drop enum if exists (cleanup from failed attempts)
    op.execute("DROP TYPE IF EXISTS waitlistpriority CASCADE")

    # Add waitlist_priority field (null for non-waitlisted enrollments)
    op.add_column(
        'enrollments',
        sa.Column(
            'waitlist_priority',
            sa.String(20),
            nullable=True
        )
    )

    # Add auto_promote flag for priority waitlist
    op.add_column(
        'enrollments',
        sa.Column(
            'auto_promote',
            sa.Boolean,
            nullable=False,
            server_default='false'
        )
    )

    # Add claim window expiration for regular waitlist
    op.add_column(
        'enrollments',
        sa.Column(
            'claim_window_expires_at',
            sa.DateTime(timezone=True),
            nullable=True
        )
    )

    # Add promoted_at timestamp to track when waitlist was promoted
    op.add_column(
        'enrollments',
        sa.Column(
            'promoted_at',
            sa.DateTime(timezone=True),
            nullable=True
        )
    )

    # Add index for querying waitlisted enrollments
    op.create_index(
        'ix_enrollments_waitlist_priority',
        'enrollments',
        ['waitlist_priority', 'created_at']
    )

    # Add index for claim window expiration queries
    op.create_index(
        'ix_enrollments_claim_expires',
        'enrollments',
        ['claim_window_expires_at']
    )


def downgrade() -> None:
    """Remove priority waitlist fields."""
    op.drop_index('ix_enrollments_claim_expires', 'enrollments')
    op.drop_index('ix_enrollments_waitlist_priority', 'enrollments')
    op.drop_column('enrollments', 'promoted_at')
    op.drop_column('enrollments', 'claim_window_expires_at')
    op.drop_column('enrollments', 'auto_promote')
    op.drop_column('enrollments', 'waitlist_priority')
