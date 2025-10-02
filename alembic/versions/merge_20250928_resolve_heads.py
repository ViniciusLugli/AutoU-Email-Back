"""merge heads

Revision ID: merge_20250928_resolve_heads
Revises: 0f3261525822, 1c9f4b2d3a4b
Create Date: 2025-09-28 12:10:00.000000

This is an empty merge migration to unify multiple heads.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'merge_20250928_resolve_heads'
down_revision: Union[str, Sequence[str], None] = ('0f3261525822', '1c9f4b2d3a4b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Empty merge migration."""
    pass


def downgrade() -> None:
    """Empty downgrade for merge migration."""
    pass
