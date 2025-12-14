"""add_account_credit_system

Revision ID: 462b747b9f1d
Revises: a3792d5ddd90
Create Date: 2025-11-30 00:22:37.058985

Adds account credit system for class transfers.
- Downgrades: Credit to account (no refund)
- Upgrades: Charge CC on file
- Credits can be applied to future purchases
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '462b747b9f1d'
down_revision: Union[str, Sequence[str], None] = 'a3792d5ddd90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add account credit system."""
    # Drop enum if it exists from failed previous attempt
    op.execute("DROP TYPE IF EXISTS credittransactiontype CASCADE")

    # Add account_credit field to users table
    op.add_column(
        'users',
        sa.Column(
            'account_credit',
            sa.Numeric(10, 2),
            nullable=False,
            server_default='0.00'
        )
    )

    # Enum will be created automatically by SQLAlchemy when creating the table

    # Create account_credit_transactions table
    op.create_table(
        'account_credit_transactions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column(
            'transaction_type',
            sa.Enum(
                'earned', 'spent', 'expired', 'refund_to_credit', 'transfer_downgrade',
                name='credittransactiontype'
            ),
            nullable=False
        ),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('order_id', sa.String(36), nullable=True),
        sa.Column('enrollment_id', sa.String(36), nullable=True),
        sa.Column('payment_id', sa.String(36), nullable=True),
        sa.Column('balance_after', sa.Numeric(10, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Add foreign key constraints
    op.create_foreign_key(
        'fk_account_credit_transactions_user_id',
        'account_credit_transactions',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_account_credit_transactions_order_id',
        'account_credit_transactions',
        'orders',
        ['order_id'],
        ['id'],
        ondelete='SET NULL'
    )

    op.create_foreign_key(
        'fk_account_credit_transactions_enrollment_id',
        'account_credit_transactions',
        'enrollments',
        ['enrollment_id'],
        ['id'],
        ondelete='SET NULL'
    )

    op.create_foreign_key(
        'fk_account_credit_transactions_payment_id',
        'account_credit_transactions',
        'payments',
        ['payment_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Add indexes
    op.create_index(
        'ix_account_credit_transactions_user_id',
        'account_credit_transactions',
        ['user_id']
    )

    op.create_index(
        'ix_account_credit_transactions_created_at',
        'account_credit_transactions',
        ['created_at']
    )


def downgrade() -> None:
    """Remove account credit system."""
    op.drop_index('ix_account_credit_transactions_created_at', 'account_credit_transactions')
    op.drop_index('ix_account_credit_transactions_user_id', 'account_credit_transactions')
    op.drop_constraint('fk_account_credit_transactions_payment_id', 'account_credit_transactions', type_='foreignkey')
    op.drop_constraint('fk_account_credit_transactions_enrollment_id', 'account_credit_transactions', type_='foreignkey')
    op.drop_constraint('fk_account_credit_transactions_order_id', 'account_credit_transactions', type_='foreignkey')
    op.drop_constraint('fk_account_credit_transactions_user_id', 'account_credit_transactions', type_='foreignkey')
    op.drop_table('account_credit_transactions')
    op.execute("DROP TYPE credittransactiontype")
    op.drop_column('users', 'account_credit')
