"""Add ig_username and ig_password to social_media_credentials

Revision ID: ab79dd7e25b8
Revises: e165afcd3c79
Create Date: 2025-07-20 15:16:39.086605

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab79dd7e25b8'
down_revision: Union[str, None] = 'e165afcd3c79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('social_media_credentials', sa.Column('ig_username', sa.String(length=255), nullable=True))
    op.add_column('social_media_credentials', sa.Column('ig_password', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('social_media_credentials', 'ig_username')
    op.drop_column('social_media_credentials', 'ig_password')
