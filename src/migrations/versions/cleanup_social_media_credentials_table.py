"""Cleanup social_media_credentials table: remove unused columns"""

revision = "cleanup123456"
down_revision = "186365742e31"
branch_labels = None
depends_on = None

from alembic import op

def upgrade():
    # Facebook
    op.drop_column('social_media_credentials', 'fb_app_id')
    op.drop_column('social_media_credentials', 'fb_app_secret')
    op.drop_column('social_media_credentials', 'fb_access_token')
    # Discord
    op.drop_column('social_media_credentials', 'discord_client_id')
    op.drop_column('social_media_credentials', 'discord_client_secret')
    op.drop_column('social_media_credentials', 'discord_bot_token')
    # LinkedIn
    op.drop_column('social_media_credentials', 'linkedin_client_id')
    op.drop_column('social_media_credentials', 'linkedin_client_secret')
    # (Add any other fields you no longer use)
    # Note: Only drop columns that actually exist in your table!

def downgrade():
    # Add columns back if needed (define types as before)
    pass 