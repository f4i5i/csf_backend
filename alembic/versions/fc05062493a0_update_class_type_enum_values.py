"""update_class_type_enum_values

Revision ID: fc05062493a0
Revises: a8a6d78eeeed
Create Date: 2025-12-14 03:33:37.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc05062493a0'
down_revision: Union[str, Sequence[str], None] = 'a8a6d78eeeed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update existing class_type values from uppercase to lowercase format."""
    # Step 1: Convert column to text temporarily
    op.execute("ALTER TABLE classes ALTER COLUMN class_type TYPE text")

    # Step 2: Update the values
    op.execute("""
        UPDATE classes
        SET class_type = 'short_term'
        WHERE class_type = 'SHORT_TERM'
    """)

    op.execute("""
        UPDATE classes
        SET class_type = 'membership'
        WHERE class_type = 'MEMBERSHIP'
    """)

    op.execute("""
        UPDATE classes
        SET class_type = 'one-time'
        WHERE class_type = 'ONE_TIME'
    """)

    # Step 3: Drop old enum type
    op.execute("DROP TYPE IF EXISTS classtype CASCADE")

    # Step 4: Create new enum type with lowercase values
    op.execute("CREATE TYPE classtype AS ENUM ('short_term', 'membership', 'one-time')")

    # Step 5: Convert column back to enum
    op.execute("ALTER TABLE classes ALTER COLUMN class_type TYPE classtype USING class_type::classtype")


def downgrade() -> None:
    """Revert class_type values back to uppercase format."""
    # Step 1: Convert column to text temporarily
    op.execute("ALTER TABLE classes ALTER COLUMN class_type TYPE text")

    # Step 2: Revert the values
    op.execute("""
        UPDATE classes
        SET class_type = 'SHORT_TERM'
        WHERE class_type = 'short_term'
    """)

    op.execute("""
        UPDATE classes
        SET class_type = 'MEMBERSHIP'
        WHERE class_type = 'membership'
    """)

    op.execute("""
        UPDATE classes
        SET class_type = 'ONE_TIME'
        WHERE class_type = 'one-time'
    """)

    # Step 3: Drop current enum type
    op.execute("DROP TYPE IF EXISTS classtype CASCADE")

    # Step 4: Recreate enum type with uppercase values
    op.execute("CREATE TYPE classtype AS ENUM ('SHORT_TERM', 'MEMBERSHIP', 'ONE_TIME')")

    # Step 5: Convert column back to enum
    op.execute("ALTER TABLE classes ALTER COLUMN class_type TYPE classtype USING class_type::classtype")
