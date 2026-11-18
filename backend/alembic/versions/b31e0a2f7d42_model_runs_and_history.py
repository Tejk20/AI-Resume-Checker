"""Record embedding/scoring provenance and retain superseded matching results."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'b31e0a2f7d42'
down_revision = 'ac6625edd2a0'
branch_labels = None
depends_on = None
J = sa.JSON().with_variant(JSONB(), 'postgresql')


def upgrade():
    op.create_table('matching_runs',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('job_id', sa.Uuid(), sa.ForeignKey('jobs.id'), nullable=False),
        sa.Column('embedding_model', sa.String(255), nullable=False),
        sa.Column('scoring_config', J, nullable=False),
        sa.Column('algorithm_version', sa.String(80), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('candidate_count', sa.Integer(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('error', sa.Text()),
        sa.CheckConstraint("status IN ('processing','completed','failed')"))
    op.create_index('ix_matching_runs_job_id', 'matching_runs', ['job_id'])
    with op.batch_alter_table('match_results', naming_convention={'ck':'ck_%(table_name)s_overall_score'}) as batch:
        batch.add_column(sa.Column('embedding_model', sa.String(255), nullable=False, server_default='legacy/unknown'))
        batch.add_column(sa.Column('scoring_config', J, nullable=False, server_default='{}'))
        batch.add_column(sa.Column('run_id', sa.Uuid(), nullable=True))
        batch.create_foreign_key('fk_match_results_run_id', 'matching_runs', ['run_id'], ['id'])
        batch.create_index('ix_match_results_run_id', ['run_id'])
    table = sa.table('match_results', sa.column('id', sa.Uuid()), sa.column('algorithm_version', sa.String()),
                     sa.column('explanation', J), sa.column('embedding_model', sa.String()), sa.column('scoring_config', J))
    connection = op.get_bind()
    for row in connection.execute(sa.select(table.c.id, table.c.algorithm_version, table.c.explanation)).mappings().all():
        model = 'sentence-transformers/all-MiniLM-L6-v2' if 'minilm' in row['algorithm_version'].lower() else 'legacy/unknown'
        config = {'effective_weights': row['explanation'].get('weights', {}),
                  'provenance': 'inferred from legacy algorithm version; no historical run metadata existed'}
        connection.execute(table.update().where(table.c.id == row['id']).values(embedding_model=model, scoring_config=config))
    op.create_table('match_result_history',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('job_id', sa.Uuid(), sa.ForeignKey('jobs.id'), nullable=False),
        sa.Column('candidate_id', sa.Uuid(), sa.ForeignKey('candidates.id'), nullable=False),
        sa.Column('previous_result_id', sa.Uuid(), nullable=False),
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('matching_runs.id')),
        sa.Column('embedding_model', sa.String(255), nullable=False),
        sa.Column('scoring_config', J, nullable=False),
        sa.Column('payload', J, nullable=False))
    op.create_index('ix_match_result_history_job_id', 'match_result_history', ['job_id'])
    op.create_index('ix_match_result_history_candidate_id', 'match_result_history', ['candidate_id'])


def downgrade():
    op.drop_table('match_result_history')
    with op.batch_alter_table('match_results', naming_convention={'ck':'ck_%(table_name)s_overall_score'}) as batch:
        batch.drop_index('ix_match_results_run_id')
        batch.drop_constraint('fk_match_results_run_id', type_='foreignkey')
        batch.drop_column('run_id')
        batch.drop_column('scoring_config')
        batch.drop_column('embedding_model')
    op.drop_table('matching_runs')
