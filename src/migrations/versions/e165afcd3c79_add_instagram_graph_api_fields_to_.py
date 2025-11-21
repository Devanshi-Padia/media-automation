"""Switch Instagram credentials to username/password for SocialMediaCredential

Revision ID: e165afcd3c79
Revises: e0bfa11e394b
Create Date: 2025-07-19 18:09:01.579373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e165afcd3c79'
down_revision: Union[str, None] = 'e0bfa11e394b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove Graph API fields, add username/password
    op.drop_column('social_media_credentials', 'ig_graph_access_token')
    op.drop_column('social_media_credentials', 'ig_user_id')
    op.add_column('social_media_credentials', sa.Column('ig_username', sa.String(length=255), nullable=True))
    op.add_column('social_media_credentials', sa.Column('ig_password', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Add Graph API fields back, remove username/password
    op.drop_column('social_media_credentials', 'ig_username')
    op.drop_column('social_media_credentials', 'ig_password')
    op.add_column('social_media_credentials', sa.Column('ig_graph_access_token', sa.String(length=255), nullable=True))
    op.add_column('social_media_credentials', sa.Column('ig_user_id', sa.String(length=255), nullable=True))
    op.drop_column('social_media_credentials', 'ig_graph_access_token')
    # ### end Alembic commands ###
