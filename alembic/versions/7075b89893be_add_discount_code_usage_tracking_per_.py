"""add_discount_code_usage_tracking_per_class

Revision ID: 7075b89893be
Revises: f3be9ace8538
Create Date: 2025-11-29 23:15:16.435383

This migration creates a discount_code_usage table to track promo code usage
per user per class, allowing users to reuse the same code for different classes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '7075b89893be'
down_revision: Union[str, Sequence[str], None] = 'f3be9ace8538'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create discount_code_usage tracking table."""
    # Create table to track usage per user per class
    op.create_table(
        'discount_code_usage',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('discount_code_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('class_id', sa.String(36), nullable=False),
        sa.Column('order_id', sa.String(36), nullable=True),
        sa.Column('used_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Add foreign key constraints
    op.create_foreign_key(
        'fk_discount_code_usage_discount_code_id',
        'discount_code_usage',
        'discount_codes',
        ['discount_code_id'],
        ['id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_discount_code_usage_user_id',
        'discount_code_usage',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_discount_code_usage_class_id',
        'discount_code_usage',
        'classes',
        ['class_id'],
        ['id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_discount_code_usage_order_id',
        'discount_code_usage',
        'orders',
        ['order_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Add unique constraint to prevent duplicate usage per user per class
    op.create_unique_constraint(
        'uq_discount_code_usage_user_class',
        'discount_code_usage',
        ['discount_code_id', 'user_id', 'class_id']
    )

    # Add indexes for better query performance
    op.create_index(
        'ix_discount_code_usage_discount_code_id',
        'discount_code_usage',
        ['discount_code_id']
    )

    op.create_index(
        'ix_discount_code_usage_user_id',
        'discount_code_usage',
        ['user_id']
    )

    op.create_index(
        'ix_discount_code_usage_class_id',
        'discount_code_usage',
        ['class_id']
    )


def downgrade() -> None:
    """Remove discount_code_usage tracking table."""
    op.drop_index('ix_discount_code_usage_class_id', 'discount_code_usage')
    op.drop_index('ix_discount_code_usage_user_id', 'discount_code_usage')
    op.drop_index('ix_discount_code_usage_discount_code_id', 'discount_code_usage')
    op.drop_constraint('uq_discount_code_usage_user_class', 'discount_code_usage', type_='unique')
    op.drop_constraint('fk_discount_code_usage_order_id', 'discount_code_usage', type_='foreignkey')
    op.drop_constraint('fk_discount_code_usage_class_id', 'discount_code_usage', type_='foreignkey')
    op.drop_constraint('fk_discount_code_usage_user_id', 'discount_code_usage', type_='foreignkey')
    op.drop_constraint('fk_discount_code_usage_discount_code_id', 'discount_code_usage', type_='foreignkey')
    op.drop_table('discount_code_usage')
