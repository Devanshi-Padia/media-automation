"""Create social_media_credentials table

Revision ID: b575720360cd
Revises: b4ed86fd19f8
Create Date: 2025-07-21 11:16:05.708729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b575720360cd'
down_revision: Union[str, None] = 'b4ed86fd19f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'social_media_credentials',
        sa.Column('id', sa.Integer(), primary_key=True, index=True, autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        # Instagram
        sa.Column('ig_username', sa.String(length=255), nullable=True),
        sa.Column('ig_password', sa.String(length=255), nullable=True),
        # Facebook
        sa.Column('fb_page_id', sa.String(length=255), nullable=True),
        sa.Column('fb_page_access_token', sa.String(length=255), nullable=True),
        # X (Twitter)
        sa.Column('twitter_api_key', sa.String(length=255), nullable=True),
        sa.Column('twitter_api_secret', sa.String(length=255), nullable=True),
        sa.Column('twitter_access_token', sa.String(length=255), nullable=True),
        sa.Column('twitter_access_secret', sa.String(length=255), nullable=True),
        # LinkedIn
        sa.Column('linkedin_access_token', sa.String(length=255), nullable=True),
        sa.Column('linkedin_author_urn', sa.String(length=255), nullable=True),
        # Discord
        sa.Column('discord_webhook_url', sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('social_media_credentials')
