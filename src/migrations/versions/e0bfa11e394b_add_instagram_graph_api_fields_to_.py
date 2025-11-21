"""Remove Instagram Graph API fields from SocialCredential

Revision ID: e0bfa11e394b
Revises: 915185357f97
Create Date: 2025-07-19 18:05:08.703579

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e0bfa11e394b'
down_revision: Union[str, None] = '915185357f97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove Graph API fields if present
    with op.batch_alter_table('social_credentials') as batch_op:
        if 'ig_graph_access_token' in [c['name'] for c in batch_op.get_columns()]:
            batch_op.drop_column('ig_graph_access_token')
        if 'ig_user_id' in [c['name'] for c in batch_op.get_columns()]:
            batch_op.drop_column('ig_user_id')


def downgrade() -> None:
    # Add Graph API fields back
    op.add_column('social_credentials', sa.Column('ig_graph_access_token', sa.String(), nullable=True))
    op.add_column('social_credentials', sa.Column('ig_user_id', sa.String(), nullable=True))
    op.create_table('token_blacklist',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('token', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('expires_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('token_blacklist_pkey'))
    )
    op.create_index(op.f('ix_token_blacklist_token'), 'token_blacklist', ['token'], unique=True)
    # ### end Alembic commands ###
