"""fix_role_enum_values

Revision ID: a55677daab6b
Revises: 4256a101e937
Create Date: 2025-11-26 23:37:20.521924

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a55677daab6b'
down_revision: Union[str, Sequence[str], None] = '4256a101e937'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix role enum to use lowercase values and replace STAFF with COACH."""
    # Create new enum with lowercase values
    op.execute("CREATE TYPE role_new AS ENUM ('owner', 'admin', 'coach', 'parent')")

    # Alter table to use new enum, converting old values to new
    op.execute("""
        ALTER TABLE users
        ALTER COLUMN role TYPE role_new
        USING (
            CASE role::text
                WHEN 'OWNER' THEN 'owner'::role_new
                WHEN 'ADMIN' THEN 'admin'::role_new
                WHEN 'STAFF' THEN 'coach'::role_new
                WHEN 'PARENT' THEN 'parent'::role_new
            END
        )
    """)

    # Drop old enum
    op.execute("DROP TYPE role")

    # Rename new enum to original name
    op.execute("ALTER TYPE role_new RENAME TO role")


def downgrade() -> None:
    """Revert role enum back to uppercase values and COACH to STAFF."""
    # Create old enum with uppercase values
    op.execute("CREATE TYPE role_old AS ENUM ('OWNER', 'ADMIN', 'STAFF', 'PARENT')")

    # Alter table to use old enum, converting new values back to old
    op.execute("""
        ALTER TABLE users
        ALTER COLUMN role TYPE role_old
        USING (
            CASE role::text
                WHEN 'owner' THEN 'OWNER'::role_old
                WHEN 'admin' THEN 'ADMIN'::role_old
                WHEN 'coach' THEN 'STAFF'::role_old
                WHEN 'parent' THEN 'PARENT'::role_old
            END
        )
    """)

    # Drop new enum
    op.execute("DROP TYPE role")

    # Rename old enum back to original name
    op.execute("ALTER TYPE role_old RENAME TO role")
