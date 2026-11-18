"""Apply current scoring policy to saved components without re-embedding documents.

Run after a scoring-weight change. Candidate evidence and semantic similarity
are unchanged; recompute explanations and totals atomically with a new version.
"""
import json
import os
import sys
from pathlib import Path
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT / 'backend')
sys.path.insert(0, str(ROOT / 'backend'))

from app.core.database import SessionLocal
from app.core.config import ALGORITHM_VERSION
from app.models import Job, MatchResult, UploadBatch, MatchingRun
from app.models.entities import now
from app.services.scoring import score_candidate
from app.services.history import archive_result
from app.core.config import WEIGHTS


def main():
    summaries = {}
    runs = {}
    with SessionLocal() as db:
        if db.scalar(select(Job.id).where(Job.match_status == 'processing')) or db.scalar(
            select(UploadBatch.id).where(UploadBatch.status.in_(['pending', 'processing']))
        ):
            raise SystemExit('Wait for active processing to finish before recalculating saved results.')
        results = db.scalars(select(MatchResult)).all()
        for result in results:
            job = db.get(Job, result.job_id)
            archive_result(db, result)
            key = (result.job_id, result.embedding_model)
            if key not in runs:
                config = {'default_weights': dict(WEIGHTS), 'operation': 'reweight_only',
                          'semantic': result.scoring_config.get('semantic', {'provenance':'legacy semantic score reused'})}
                run = MatchingRun(job_id=result.job_id, embedding_model=result.embedding_model,
                    scoring_config=config, algorithm_version='2.0.0-reweight-only', status='completed',
                    candidate_count=0, completed_at=now())
                db.add(run); db.flush(); runs[key]=run
            run = runs[key]
            run.candidate_count += 1
            values = score_candidate(job, result.candidate, result.semantic_score,
                                     result.explanation.get('semantic_evidence', []))
            values.update(algorithm_version='2.0.0-reweight-only', scoring_config=run.scoring_config, run_id=run.id)
            for key, value in values.items():
                setattr(result, key, value)
            result.created_at = now()
            summaries.setdefault(str(result.job_id), []).append({
                'name': result.candidate.name,
                'score': result.overall_score,
            })
        db.commit()
        print(f'Reweighted {len(results)} saved results; semantic models/scores preserved and previous results archived.')
    for job_id, rows in summaries.items():
        rows.sort(key=lambda row: row['score'], reverse=True)
        print(job_id, 'top:', rows[0]['name'], rows[0]['score'])
    # Refresh the local synthetic verification artifact, if present.
    report_path = ROOT / 'test-artifacts/workflow-report.json'
    if report_path.exists():
        report = json.loads(report_path.read_text())
        for item in report:
            rows = summaries.get(item['job_id'])
            if rows:
                item.update(top_candidate=rows[0]['name'], top_score=rows[0]['score'],
                            bottom_candidate=rows[-1]['name'], bottom_score=rows[-1]['score'],
                            algorithm_version='2.0.0-reweight-only')
        report_path.write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
