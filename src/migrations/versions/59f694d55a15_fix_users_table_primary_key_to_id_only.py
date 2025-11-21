"""Fix users table primary key to id only

Revision ID: 59f694d55a15
Revises: 887f27aba7a8
Create Date: 2025-07-25 14:45:10.628742

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59f694d55a15'
down_revision: Union[str, None] = '887f27aba7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Drop the old composite primary key
    op.drop_constraint('users_pkey', 'users', type_='primary')
    # Create a new primary key on id only
    op.create_primary_key('users_pkey', 'users', ['id'])

def downgrade():
    # Drop the single-column primary key
    op.drop_constraint('users_pkey', 'users', type_='primary')
    # Restore the composite primary key
    op.create_primary_key('users_pkey', 'users', ['id', 'uuid'])
