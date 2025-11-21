"""Make post_id nullable and add project_id to scheduled_posts

Revision ID: 2c2e266a364e
Revises: 02122109854c
Create Date: 2025-07-22 16:22:29.048032

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c2e266a364e'
down_revision: Union[str, None] = '02122109854c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make post_id nullable
    op.alter_column('scheduled_posts', 'post_id',
        existing_type=sa.Integer(),
        nullable=True
    )
    # Add project_id column
    op.add_column('scheduled_posts', sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=True))


def downgrade() -> None:
    # Remove project_id column
    op.drop_column('scheduled_posts', 'project_id')
    # Make post_id NOT NULL again
    op.alter_column('scheduled_posts', 'post_id',
        existing_type=sa.Integer(),
        nullable=False
    )
