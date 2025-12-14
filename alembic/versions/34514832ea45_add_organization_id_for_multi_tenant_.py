"""add_organization_id_for_multi_tenant_support

Revision ID: 34514832ea45
Revises: 68351cdd13a9
Create Date: 2025-11-29

This migration adds multi-tenant support by creating an organizations table
and adding organization_id to all tables. This is critical for future scalability
even if currently serving only one organization.

IMPORTANT: This migration includes data migration to set a default organization
for all existing records.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = '34514832ea45'
down_revision: Union[str, Sequence[str], None] = '68351cdd13a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add organizations table and organization_id to all tables."""

    # 1. Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])
    op.create_index('ix_organizations_is_active', 'organizations', ['is_active'])

    # 2. Insert default organization for existing data
    op.execute("""
        INSERT INTO organizations (id, name, slug, description, is_active, created_at, updated_at)
        VALUES (
            'default-org-00000000000000000000',
            'Default Organization',
            'default',
            'Auto-created organization for existing data',
            true,
            NOW(),
            NOW()
        )
    """)

    # 3. Add organization_id to all tables
    tables_to_update = [
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
    ]

    for table in tables_to_update:
        # Add organization_id column (nullable first)
        op.add_column(
            table,
            sa.Column('organization_id', sa.String(36), nullable=True)
        )

        # Set default organization for existing records
        op.execute(f"""
            UPDATE {table}
            SET organization_id = 'default-org-00000000000000000000'
            WHERE organization_id IS NULL
        """)

        # Make it NOT NULL after data migration
        op.alter_column(table, 'organization_id', nullable=False)

        # Add foreign key constraint
        op.create_foreign_key(
            f'fk_{table}_organization_id',
            table,
            'organizations',
            ['organization_id'],
            ['id']
        )

        # Add index for better query performance
        op.create_index(
            f'ix_{table}_organization_id',
            table,
            ['organization_id']
        )

    # 4. Update unique constraints to include organization_id

    # Users: email must be unique per organization (not globally)
    op.drop_index('ix_users_email', 'users')
    op.create_index(
        'ix_users_organization_email',
        'users',
        ['organization_id', 'email'],
        unique=True
    )

    # Discount codes: code must be unique per organization
    op.drop_index('ix_discount_codes_code', 'discount_codes')
    op.create_unique_constraint(
        'uq_discount_codes_organization_code',
        'discount_codes',
        ['organization_id', 'code']
    )

    # Enrollments: child + class must be unique per organization
    op.create_unique_constraint(
        'uq_enrollment_child_class_organization',
        'enrollments',
        ['organization_id', 'child_id', 'class_id']
    )

    # Photo categories: class + name unique per organization
    op.drop_constraint('unique_class_category', 'photo_categories', type_='unique')
    op.create_unique_constraint(
        'uq_photo_categories_organization_class_name',
        'photo_categories',
        ['organization_id', 'class_id', 'name']
    )


def downgrade() -> None:
    """Remove organization_id and organizations table."""

    tables_to_update = [
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
    ]

    # Remove unique constraints
    op.drop_constraint('uq_enrollment_child_class_organization', 'enrollments', type_='unique')
    op.drop_constraint('uq_photo_categories_organization_class_name', 'photo_categories', type_='unique')
    op.drop_constraint('uq_discount_codes_organization_code', 'discount_codes', type_='unique')

    # Restore original constraints
    op.create_index('ix_discount_codes_code', 'discount_codes', ['code'], unique=True)
    op.create_unique_constraint('unique_class_category', 'photo_categories', ['class_id', 'name'])

    # Restore original user email index
    op.drop_index('ix_users_organization_email', 'users')
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Remove organization_id from all tables
    for table in tables_to_update:
        op.drop_index(f'ix_{table}_organization_id', table)
        op.drop_constraint(f'fk_{table}_organization_id', table, type_='foreignkey')
        op.drop_column(table, 'organization_id')

    # Drop organizations table
    op.drop_index('ix_organizations_is_active', 'organizations')
    op.drop_index('ix_organizations_slug', 'organizations')
    op.drop_table('organizations')
