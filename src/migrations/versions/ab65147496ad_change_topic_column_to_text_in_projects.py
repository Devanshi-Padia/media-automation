"""Change topic column to Text in projects

Revision ID: ab65147496ad
Revises: 81781416bd17
Create Date: 2025-07-17 14:44:13.149930

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab65147496ad'
down_revision: Union[str, None] = '81781416bd17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('projects', 'topic', type_=sa.Text())


def downgrade() -> None:
    pass
