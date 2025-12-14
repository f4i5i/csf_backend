"""add_soft_delete_fields_to_all_tables

Revision ID: ada926e19a3d
Revises: 34514832ea45
Create Date: 2025-11-29 18:00:01.431166

This migration adds soft delete support by adding is_deleted and deleted_at
fields to all tables. This allows for data recovery and audit trails.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ada926e19a3d'
down_revision: Union[str, Sequence[str], None] = '34514832ea45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_deleted and deleted_at columns to all tables."""

    # List of all tables that need soft delete functionality
    tables = [
        'users',
        'children',
        'emergency_contacts',
        'programs',
        'areas',
        'schools',
        'classes',
        'enrollments',
        'orders',
        'order_line_items',
        'payments',
        'installment_plans',
        'installment_payments',
        'waiver_templates',
        'waiver_acceptances',
        'discount_codes',
        'scholarships',
        'password_history',
        'attendances',
        'checkins',
        'events',
        'photos',
        'photo_categories',
        'badges',
        'student_badges',
        'announcements',
        'announcement_attachments',
        'announcement_targets',
        'organizations',
    ]

    for table in tables:
        # Add is_deleted column
        op.add_column(
            table,
            sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false')
        )

        # Add deleted_at column
        op.add_column(
            table,
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
        )

        # Add index on is_deleted for better query performance
        op.create_index(
            f'ix_{table}_is_deleted',
            table,
            ['is_deleted']
        )


def downgrade() -> None:
    """Remove is_deleted and deleted_at columns from all tables."""

    tables = [
        'users',
        'children',
        'emergency_contacts',
        'programs',
        'areas',
        'schools',
        'classes',
        'enrollments',
        'orders',
        'order_line_items',
        'payments',
        'installment_plans',
        'installment_payments',
        'waiver_templates',
        'waiver_acceptances',
        'discount_codes',
        'scholarships',
        'password_history',
        'attendances',
        'checkins',
        'events',
        'photos',
        'photo_categories',
        'badges',
        'student_badges',
        'announcements',
        'announcement_attachments',
        'announcement_targets',
        'organizations',
    ]

    for table in tables:
        op.drop_index(f'ix_{table}_is_deleted', table)
        op.drop_column(table, 'deleted_at')
        op.drop_column(table, 'is_deleted')
