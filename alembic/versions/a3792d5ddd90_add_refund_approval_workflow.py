"""add_refund_approval_workflow

Revision ID: a3792d5ddd90
Revises: 7075b89893be
Create Date: 2025-11-30 00:04:14.269733

Adds refund approval workflow fields to payments table.
All refunds now require admin approval before processing.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3792d5ddd90'
down_revision: Union[str, Sequence[str], None] = '7075b89893be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add refund approval workflow fields."""
    # Create RefundStatus enum type
    op.execute("""
        CREATE TYPE refundstatus AS ENUM (
            'not_requested',
            'pending',
            'approved',
            'rejected'
        )
    """)

    # Add refund approval fields to payments table
    op.add_column(
        'payments',
        sa.Column(
            'refund_status',
            sa.Enum('not_requested', 'pending', 'approved', 'rejected', name='refundstatus'),
            nullable=False,
            server_default='not_requested'
        )
    )

    op.add_column(
        'payments',
        sa.Column('refund_requested_at', sa.DateTime(timezone=True), nullable=True)
    )

    op.add_column(
        'payments',
        sa.Column('refund_approved_by_id', sa.String(36), nullable=True)
    )

    op.add_column(
        'payments',
        sa.Column('refund_approved_at', sa.DateTime(timezone=True), nullable=True)
    )

    op.add_column(
        'payments',
        sa.Column('refund_rejection_reason', sa.Text, nullable=True)
    )

    # Add foreign key for approved_by
    op.create_foreign_key(
        'fk_payments_refund_approved_by_id',
        'payments',
        'users',
        ['refund_approved_by_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Add index for refund status queries
    op.create_index(
        'ix_payments_refund_status',
        'payments',
        ['refund_status']
    )


def downgrade() -> None:
    """Remove refund approval workflow fields."""
    op.drop_index('ix_payments_refund_status', 'payments')
    op.drop_constraint('fk_payments_refund_approved_by_id', 'payments', type_='foreignkey')
    op.drop_column('payments', 'refund_rejection_reason')
    op.drop_column('payments', 'refund_approved_at')
    op.drop_column('payments', 'refund_approved_by_id')
    op.drop_column('payments', 'refund_requested_at')
    op.drop_column('payments', 'refund_status')

    # Drop enum type
    op.execute("DROP TYPE refundstatus")
