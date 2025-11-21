"""Manual remove platforms from ContentGeneration

Revision ID: deb3091fd41b
Revises: d3496a7d055e
Create Date: 2024-07-29 13:06:56.536109

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'deb3091fd41b'
down_revision: Union[str, None] = 'd3496a7d055e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This migration is now empty as the operation is handled by 715143cb8667
    pass


def downgrade() -> None:
    # This migration is now empty as the operation is handled by 715143cb8667
    pass
