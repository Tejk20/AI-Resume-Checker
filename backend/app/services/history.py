"""History is written in the same transaction as replacement/invalidation."""
from copy import deepcopy
from app.models import MatchResultHistory


def archive_result(db, result):
    payload = {key: getattr(result, key) for key in [
        'overall_score', 'semantic_score', 'skill_score', 'experience_score', 'education_score',
        'matched_skills', 'missing_skills', 'explanation', 'algorithm_version']}
    payload['evaluated_at'] = result.created_at.isoformat()
    db.add(MatchResultHistory(job_id=result.job_id, candidate_id=result.candidate_id,
        previous_result_id=result.id, run_id=result.run_id,
        embedding_model=result.embedding_model, scoring_config=deepcopy(result.scoring_config),
        payload=deepcopy(payload)))
