"""Add ig_username and ig_password to social_media_credentials

Revision ID: 38a678784a2d
Revises: fa70fba0fd88
Create Date: 2025-07-20 17:08:26.350657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38a678784a2d'
down_revision: Union[str, None] = 'fa70fba0fd88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('social_media_credentials', sa.Column('ig_username', sa.String(length=255), nullable=True))
    op.add_column('social_media_credentials', sa.Column('ig_password', sa.String(length=255), nullable=True))
    op.alter_column('social_media_credentials', 'linkedin_access_token', type_=sa.Text())
    op.alter_column('social_media_credentials', 'linkedin_client_secret', type_=sa.Text())
    op.alter_column('social_media_credentials', 'linkedin_client_id', type_=sa.Text())
    op.alter_column('social_media_credentials', 'twitter_access_token', type_=sa.Text())
    op.alter_column('social_media_credentials', 'twitter_access_secret', type_=sa.Text())
    op.alter_column('social_media_credentials', 'discord_bot_token', type_=sa.Text())
    op.alter_column('social_media_credentials', 'discord_webhook_url', type_=sa.Text())


def downgrade() -> None:
    op.drop_column('social_media_credentials', 'ig_username')
    op.drop_column('social_media_credentials', 'ig_password')
    op.alter_column('social_media_credentials', 'linkedin_access_token', type_=sa.String(length=255))
    op.alter_column('social_media_credentials', 'linkedin_client_secret', type_=sa.String(length=255))
    op.alter_column('social_media_credentials', 'linkedin_client_id', type_=sa.String(length=255))
    op.alter_column('social_media_credentials', 'twitter_access_token', type_=sa.String(length=255))
    op.alter_column('social_media_credentials', 'twitter_access_secret', type_=sa.String(length=255))
    op.alter_column('social_media_credentials', 'discord_bot_token', type_=sa.String(length=255))
    op.alter_column('social_media_credentials', 'discord_webhook_url', type_=sa.String(length=255))
