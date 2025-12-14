"""add_missing_indexes_on_foreign_keys

Revision ID: 68351cdd13a9
Revises: a55677daab6b
Create Date: 2025-11-29

This migration adds missing indexes on foreign key columns to improve
query performance. Without these indexes, filtering and joining on
these columns requires full table scans.

Performance Impact: HIGH - These indexes will significantly speed up
queries that filter or join on these foreign keys.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '68351cdd13a9'
down_revision: Union[str, Sequence[str], None] = 'a55677daab6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing indexes on foreign keys for better query performance."""

    # Classes table - program_id and school_id are heavily queried
    op.create_index(
        'ix_classes_program_id',
        'classes',
        ['program_id'],
        unique=False
    )
    op.create_index(
        'ix_classes_school_id',
        'classes',
        ['school_id'],
        unique=False
    )

    # Schools table - area_id for filtering schools by area
    op.create_index(
        'ix_schools_area_id',
        'schools',
        ['area_id'],
        unique=False
    )

    # Emergency contacts - child_id for loading all contacts for a child
    op.create_index(
        'ix_emergency_contacts_child_id',
        'emergency_contacts',
        ['child_id'],
        unique=False
    )

    # Waiver templates - applies_to fields for finding relevant waivers
    op.create_index(
        'ix_waiver_templates_applies_to_program_id',
        'waiver_templates',
        ['applies_to_program_id'],
        unique=False
    )
    op.create_index(
        'ix_waiver_templates_applies_to_school_id',
        'waiver_templates',
        ['applies_to_school_id'],
        unique=False
    )

    # Waiver acceptances - waiver_template_id for finding all acceptances
    op.create_index(
        'ix_waiver_acceptances_waiver_template_id',
        'waiver_acceptances',
        ['waiver_template_id'],
        unique=False
    )

    # Order line items - critical for order processing
    op.create_index(
        'ix_order_line_items_order_id',
        'order_line_items',
        ['order_id'],
        unique=False
    )
    op.create_index(
        'ix_order_line_items_enrollment_id',
        'order_line_items',
        ['enrollment_id'],
        unique=False
    )
    op.create_index(
        'ix_order_line_items_discount_code_id',
        'order_line_items',
        ['discount_code_id'],
        unique=False
    )

    # Discount codes - for finding applicable discounts
    op.create_index(
        'ix_discount_codes_applies_to_program_id',
        'discount_codes',
        ['applies_to_program_id'],
        unique=False
    )
    op.create_index(
        'ix_discount_codes_applies_to_class_id',
        'discount_codes',
        ['applies_to_class_id'],
        unique=False
    )
    op.create_index(
        'ix_discount_codes_created_by_id',
        'discount_codes',
        ['created_by_id'],
        unique=False
    )

    # Scholarships - child_id and approved_by_id for filtering
    op.create_index(
        'ix_scholarships_child_id',
        'scholarships',
        ['child_id'],
        unique=False
    )
    op.create_index(
        'ix_scholarships_approved_by_id',
        'scholarships',
        ['approved_by_id'],
        unique=False
    )

    # Attendance - marked_by for audit trail
    op.create_index(
        'ix_attendances_marked_by',
        'attendances',
        ['marked_by'],
        unique=False
    )

    # Events - created_by for filtering events by creator
    op.create_index(
        'ix_events_created_by',
        'events',
        ['created_by'],
        unique=False
    )

    # Photos - uploaded_by for filtering photos by uploader
    op.create_index(
        'ix_photos_uploaded_by',
        'photos',
        ['uploaded_by'],
        unique=False
    )

    # Student badges - awarded_by for audit trail
    op.create_index(
        'ix_student_badges_awarded_by',
        'student_badges',
        ['awarded_by'],
        unique=False
    )

    # Installment payments - critical for payment processing
    op.create_index(
        'ix_installment_payments_installment_plan_id',
        'installment_payments',
        ['installment_plan_id'],
        unique=False
    )
    op.create_index(
        'ix_installment_payments_payment_id',
        'installment_payments',
        ['payment_id'],
        unique=False
    )


def downgrade() -> None:
    """Remove the indexes."""

    # Drop all indexes in reverse order
    op.drop_index('ix_installment_payments_payment_id', table_name='installment_payments')
    op.drop_index('ix_installment_payments_installment_plan_id', table_name='installment_payments')
    op.drop_index('ix_student_badges_awarded_by', table_name='student_badges')
    op.drop_index('ix_photos_uploaded_by', table_name='photos')
    op.drop_index('ix_events_created_by', table_name='events')
    op.drop_index('ix_attendances_marked_by', table_name='attendances')
    op.drop_index('ix_scholarships_approved_by_id', table_name='scholarships')
    op.drop_index('ix_scholarships_child_id', table_name='scholarships')
    op.drop_index('ix_discount_codes_created_by_id', table_name='discount_codes')
    op.drop_index('ix_discount_codes_applies_to_class_id', table_name='discount_codes')
    op.drop_index('ix_discount_codes_applies_to_program_id', table_name='discount_codes')
    op.drop_index('ix_order_line_items_discount_code_id', table_name='order_line_items')
    op.drop_index('ix_order_line_items_enrollment_id', table_name='order_line_items')
    op.drop_index('ix_order_line_items_order_id', table_name='order_line_items')
    op.drop_index('ix_waiver_acceptances_waiver_template_id', table_name='waiver_acceptances')
    op.drop_index('ix_waiver_templates_applies_to_school_id', table_name='waiver_templates')
    op.drop_index('ix_waiver_templates_applies_to_program_id', table_name='waiver_templates')
    op.drop_index('ix_emergency_contacts_child_id', table_name='emergency_contacts')
    op.drop_index('ix_schools_area_id', table_name='schools')
    op.drop_index('ix_classes_school_id', table_name='classes')
    op.drop_index('ix_classes_program_id', table_name='classes')
