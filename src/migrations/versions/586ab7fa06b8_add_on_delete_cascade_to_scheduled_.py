"""Add ON DELETE CASCADE to scheduled_posts.project_id

Revision ID: 586ab7fa06b8
Revises: 84545ebbd9e1
Create Date: 2025-07-25 10:29:53.849934

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '586ab7fa06b8'
down_revision: Union[str, None] = '84545ebbd9e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Drop the old constraint
    op.drop_constraint('scheduled_posts_project_id_fkey', 'scheduled_posts', type_='foreignkey')
    # Add the new constraint with ON DELETE CASCADE
    op.create_foreign_key(
        'scheduled_posts_project_id_fkey',
        'scheduled_posts', 'projects',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    # Drop the cascade constraint
    op.drop_constraint('scheduled_posts_project_id_fkey', 'scheduled_posts', type_='foreignkey')
    # Re-add the original constraint without cascade
    op.create_foreign_key(
        'scheduled_posts_project_id_fkey',
        'scheduled_posts', 'projects',
        ['project_id'], ['id']
    )
