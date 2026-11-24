"""Allow job owners to publish openings."""
from alembic import op
import sqlalchemy as sa

revision = '62bf6c90b495'
down_revision = 'f53cd41902e8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('jobs', sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column('jobs', 'is_published')
