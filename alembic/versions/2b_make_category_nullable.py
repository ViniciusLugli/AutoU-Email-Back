"""make category nullable on textentry

Revision ID: 2b_make_category_nullable
Revises: merge_20250928_resolve_heads
Create Date: 2025-09-30 17:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2b_make_category_nullable'
down_revision: Union[str, Sequence[str], None] = 'merge_20250928_resolve_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make category column nullable to match models."""
    # Alter the column to allow NULL
    op.alter_column('textentry', 'category', existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    """Revert category column to NOT NULL (use with caution)."""
    # Set a server_default to avoid failing on existing NULLs when reverting.
    op.alter_column('textentry', 'category', existing_type=sa.String(), nullable=False, server_default='Improdutivo')
