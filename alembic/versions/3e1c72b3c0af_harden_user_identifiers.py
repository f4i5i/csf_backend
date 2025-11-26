"""Ensure google_id uniqueness

Revision ID: 3e1c72b3c0af
Revises: de9363e92d3d
Create Date: 2025-11-23 23:15:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3e1c72b3c0af"
down_revision: Union[str, Sequence[str], None] = "de9363e92d3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a unique constraint so Google IDs cannot collide."""
    op.create_unique_constraint("uq_users_google_id", "users", ["google_id"])


def downgrade() -> None:
    """Drop the Google ID unique constraint."""
    op.drop_constraint("uq_users_google_id", "users", type_="unique")
