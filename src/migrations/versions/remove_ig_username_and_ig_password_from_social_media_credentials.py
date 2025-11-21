"""Remove ig_username and ig_password from social_media_credentials"""

revision = "fa70fba0fd88"  # This should match the filename prefix
down_revision = "ab79dd7e25b8"  # Set this to the previous migration's revision ID
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('social_media_credentials')]
    with op.batch_alter_table('social_media_credentials') as batch_op:
        if 'ig_username' in columns:
            batch_op.drop_column('ig_username')
        if 'ig_password' in columns:
            batch_op.drop_column('ig_password')

def downgrade():
    with op.batch_alter_table('social_media_credentials') as batch_op:
        batch_op.add_column(sa.Column('ig_username', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('ig_password', sa.String(length=255), nullable=True)) 