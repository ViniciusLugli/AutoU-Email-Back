"""convert category column to varchar safely

Revision ID: 3_convert_category_to_varchar
Revises: 2b_make_category_nullable
Create Date: 2025-09-30 21:45:00.000000

This migration attempts to make sure the `category` column on `textentry` is
stored as a plain string (varchar/text) rather than a Postgres enum type.
It uses a safe `USING` clause and best-effort steps to handle either case.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3_convert_category_to_varchar'
down_revision: Union[str, Sequence[str], None] = '2b_make_category_nullable'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert category column to VARCHAR (text) with safe casting.

    This migration will:
    - If the column is an enum type, ALTER the column to TEXT using a cast.
    - Otherwise, ALTER the column type to VARCHAR using USING category::text.
    """
    conn = op.get_bind()
    # Best-effort: try to alter column type using USING cast which works
    # both for enum and text columns.
    op.execute(
        """
        ALTER TABLE textentry
        ALTER COLUMN category TYPE VARCHAR
        USING category::text
        """
    )


def downgrade() -> None:
    """Downgrade is a no-op: reverting to a DB enum is destructive and
    environment-specific. To revert, create a custom migration that
    recreates the enum type and casts values back.
    """
    # Intentionally left as a no-op. Manual intervention required if you
    # need to convert back to a Postgres enum type.
    pass
