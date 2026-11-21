"""Optional hashed temporary password on recovery requests."""
from alembic import op
import sqlalchemy as sa

revision = 'f53cd41902e8'
down_revision = 'e42bc30891d7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('password_reset_tokens', sa.Column('temporary_password_hash', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('password_reset_tokens', 'temporary_password_hash')
