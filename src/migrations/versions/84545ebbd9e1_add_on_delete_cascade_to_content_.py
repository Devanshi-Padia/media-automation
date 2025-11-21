"""Add ON DELETE CASCADE to content_generations.project_id

Revision ID: 84545ebbd9e1
Revises: 2c2e266a364e
Create Date: 2025-07-24 10:10:51.127389

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84545ebbd9e1'
down_revision: Union[str, None] = '2c2e266a364e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Drop the old constraint
    op.drop_constraint('content_generations_project_id_fkey', 'content_generations', type_='foreignkey')
    # Add the new constraint with ON DELETE CASCADE
    op.create_foreign_key(
        'content_generations_project_id_fkey',
        'content_generations', 'projects',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )

def downgrade():
    # Drop the cascade constraint
    op.drop_constraint('content_generations_project_id_fkey', 'content_generations', type_='foreignkey')
    # Re-add the original constraint without cascade
    op.create_foreign_key(
        'content_generations_project_id_fkey',
        'content_generations', 'projects',
        ['project_id'], ['id']
    )
