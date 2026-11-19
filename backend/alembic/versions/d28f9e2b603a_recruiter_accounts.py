"""Recruiter accounts, expiring sessions and job ownership; preserve existing rows."""
from alembic import op
import sqlalchemy as sa

revision = 'd28f9e2b603a'
down_revision = 'b31e0a2f7d42'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(254), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False))
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_table('auth_sessions',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_auth_sessions_token_hash', 'auth_sessions', ['token_hash'], unique=True)
    op.create_index('ix_auth_sessions_user_id', 'auth_sessions', ['user_id'])
    op.create_index('ix_auth_sessions_expires_at', 'auth_sessions', ['expires_at'])
    with op.batch_alter_table('jobs') as batch:
        batch.add_column(sa.Column('owner_id', sa.Uuid(), nullable=True))
        batch.add_column(sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_foreign_key('fk_jobs_owner_id', 'users', ['owner_id'], ['id'])
        batch.create_index('ix_jobs_owner_id', ['owner_id'])


def downgrade():
    with op.batch_alter_table('jobs') as batch:
        batch.drop_index('ix_jobs_owner_id')
        batch.drop_constraint('fk_jobs_owner_id', type_='foreignkey')
        batch.drop_column('is_demo')
        batch.drop_column('owner_id')
    op.drop_table('auth_sessions')
    op.drop_table('users')
