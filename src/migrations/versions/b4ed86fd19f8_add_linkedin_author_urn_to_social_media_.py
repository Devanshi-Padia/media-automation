"""Add linkedin_author_urn to social_media_credentials

Revision ID: b4ed86fd19f8
Revises: cleanup123456
Create Date: 2025-07-20 23:06:15.636284

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4ed86fd19f8'
down_revision: Union[str, None] = 'cleanup123456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('social_media_credentials', sa.Column('linkedin_author_urn', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('social_media_credentials', 'linkedin_author_urn')
