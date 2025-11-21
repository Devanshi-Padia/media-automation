"""Merge heads

Revision ID: 5599c9629acb
Revises: 715143cb8667, deb3091fd41b
Create Date: 2025-07-21 15:32:21.665257

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5599c9629acb'
down_revision: Union[str, None] = ('715143cb8667', 'deb3091fd41b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
