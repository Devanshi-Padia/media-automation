"""add analytics tables

Revision ID: add_analytics_tables
Revises: 59f694d55a15
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_analytics_tables'
down_revision = '59f694d55a15'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create post_analytics table
    op.create_table('post_analytics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('post_url', sa.String(length=500), nullable=True),
        sa.Column('likes', sa.Integer(), nullable=True),
        sa.Column('shares', sa.Integer(), nullable=True),
        sa.Column('comments', sa.Integer(), nullable=True),
        sa.Column('reach', sa.Integer(), nullable=True),
        sa.Column('impressions', sa.Integer(), nullable=True),
        sa.Column('clicks', sa.Integer(), nullable=True),
        sa.Column('engagement_rate', sa.Float(), nullable=True),
        sa.Column('click_through_rate', sa.Float(), nullable=True),
        sa.Column('ab_test_id', sa.String(length=100), nullable=True),
        sa.Column('variant', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_synced', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['post_id'], ['post.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_post_analytics_post_id'), 'post_analytics', ['post_id'], unique=False)
    op.create_index(op.f('ix_post_analytics_project_id'), 'post_analytics', ['project_id'], unique=False)
    op.create_index(op.f('ix_post_analytics_ab_test_id'), 'post_analytics', ['ab_test_id'], unique=False)

    # Create ab_tests table
    op.create_table('ab_tests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('test_id', sa.String(length=100), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('test_type', sa.String(length=50), nullable=False),
        sa.Column('variants', sa.JSON(), nullable=False),
        sa.Column('traffic_split', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('winner', sa.String(length=50), nullable=True),
        sa.Column('confidence_level', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('test_id')
    )
    op.create_index(op.f('ix_ab_tests_project_id'), 'ab_tests', ['project_id'], unique=False)

    # Create analytics_reports table
    op.create_table('analytics_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_id', sa.String(length=100), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('report_name', sa.String(length=200), nullable=False),
        sa.Column('date_range', sa.JSON(), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('summary', sa.JSON(), nullable=True),
        sa.Column('format', sa.String(length=20), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_id')
    )
    op.create_index(op.f('ix_analytics_reports_project_id'), 'analytics_reports', ['project_id'], unique=False)
    op.create_index(op.f('ix_analytics_reports_user_id'), 'analytics_reports', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop analytics_reports table
    op.drop_index(op.f('ix_analytics_reports_user_id'), table_name='analytics_reports')
    op.drop_index(op.f('ix_analytics_reports_project_id'), table_name='analytics_reports')
    op.drop_table('analytics_reports')

    # Drop ab_tests table
    op.drop_index(op.f('ix_ab_tests_project_id'), table_name='ab_tests')
    op.drop_table('ab_tests')

    # Drop post_analytics table
    op.drop_index(op.f('ix_post_analytics_ab_test_id'), table_name='post_analytics')
    op.drop_index(op.f('ix_post_analytics_project_id'), table_name='post_analytics')
    op.drop_index(op.f('ix_post_analytics_post_id'), table_name='post_analytics')
    op.drop_table('post_analytics') 