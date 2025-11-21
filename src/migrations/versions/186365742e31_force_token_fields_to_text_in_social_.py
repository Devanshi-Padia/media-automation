"""Force token fields to Text in social_media_credentials

Revision ID: 186365742e31
Revises: 38a678784a2d
Create Date: 2025-07-20 22:09:21.777380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '186365742e31'
down_revision: Union[str, None] = '38a678784a2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('social_media_credentials', 'linkedin_access_token', type_=sa.Text(), existing_type=sa.String(length=255))
    op.alter_column('social_media_credentials', 'linkedin_client_secret', type_=sa.Text(), existing_type=sa.String(length=255))
    op.alter_column('social_media_credentials', 'linkedin_client_id', type_=sa.Text(), existing_type=sa.String(length=255))
    op.alter_column('social_media_credentials', 'twitter_access_token', type_=sa.Text(), existing_type=sa.String(length=255))
    op.alter_column('social_media_credentials', 'twitter_access_secret', type_=sa.Text(), existing_type=sa.String(length=255))
    op.alter_column('social_media_credentials', 'discord_bot_token', type_=sa.Text(), existing_type=sa.String(length=255))
    op.alter_column('social_media_credentials', 'discord_webhook_url', type_=sa.Text(), existing_type=sa.String(length=255))


def downgrade() -> None:
    op.alter_column('social_media_credentials', 'linkedin_access_token', type_=sa.String(length=255), existing_type=sa.Text())
    op.alter_column('social_media_credentials', 'linkedin_client_secret', type_=sa.String(length=255), existing_type=sa.Text())
    op.alter_column('social_media_credentials', 'linkedin_client_id', type_=sa.String(length=255), existing_type=sa.Text())
    op.alter_column('social_media_credentials', 'twitter_access_token', type_=sa.String(length=255), existing_type=sa.Text())
    op.alter_column('social_media_credentials', 'twitter_access_secret', type_=sa.String(length=255), existing_type=sa.Text())
    op.alter_column('social_media_credentials', 'discord_bot_token', type_=sa.String(length=255), existing_type=sa.Text())
    op.alter_column('social_media_credentials', 'discord_webhook_url', type_=sa.String(length=255), existing_type=sa.Text())
