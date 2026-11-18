# MPNet upgrade inventory

This upgrade extends the existing application. It does not create a second app or publish source to GitHub.

## Backend files changed

- `backend/app/core/config.py`: MPNet default, EMBEDDING_MODEL/MODEL_NAME compatibility, configurable batching/cache size and validated 25/40/25/10 weights; algorithm 2.0.0.
- `backend/app/services/semantic.py`: section-aware, tokenizer-bounded retrieval, model singleton, normalized batched vectors and model-specific bounded LRU caching.
- `backend/app/services/scoring.py`: bounded component validation, separate uncertain requirements, semantic-section fallback warnings and estimated job-fit wording.
- `backend/app/services/workers.py`: batched evaluation, run provenance, atomic replacement/history and failed-run/restart recovery.
- `backend/app/services/history.py`: new atomic snapshot helper.
- `backend/app/models/entities.py` and `models/__init__.py`: run and history entities, result model/configuration/run fields.
- `backend/app/schemas/contracts.py`: provenance and history/run response contracts.
- `backend/app/api/routes.py`: run/history routes; requirement edits archive current results before invalidation.
- `backend/alembic/versions/b31e0a2f7d42_model_runs_and_history.py`: additive migration, preserving legacy rows and known/unknown model provenance.
- `backend/.env.example`: model selection, cache/batch controls, validated weight configuration.
- `backend/tests/test_semantic.py`: new unit and opt-in actual-model tests.
- `backend/tests/test_api.py`: history persistence, duplicate-free rematching and failure atomicity tests.

## Frontend files changed

- `frontend/src/pages/Analysis.jsx`: estimated score, actual embedding model, recorded formula, labelled components/sections, separate uncertainty and previous evaluations.
- `frontend/src/pages/Analysis.test.jsx`: corresponding recruiter-facing interaction/rendering checks.

The existing About/features page and other application workflows are preserved.

## Scripts and documentation

- `scripts/download_model.py`: configurable model download and dimensionality/token diagnostics.
- `scripts/recalculate_scores.py`: weight-only updates now retain semantic provenance, create a labelled run and archive previous scores. Use full matching to generate MPNet semantics.
- `scripts/compare_models.py`: fresh subprocess per model; synthetic ranking, semantic, CPU-time and optional RSS comparisons.
- `scripts/verify_mpnet_upgrade.py`: isolated real PostgreSQL/HTTP/model-switch/rematch/restart test.
- `scripts/rematch_saved_jobs.py`: refresh live results and verify retained prior evaluations without reuploading resumes.
- `scripts/verify_saved_results.py`: verify current rankings and historical reference scores without treating intentional model changes or added candidates as lost persistence.
- `README.md`, `docs/matching-algorithm.md`, `docs/demo-guide.md`, `docs/architecture.md`, `docs/api-documentation.md`, `docs/verification.md`: setup, matching, provenance, switching and observed validation.
- `docs/model-comparison.md`: generated measured comparison with per-candidate ranking/semantic changes.

No new paid service or runtime package is required. Existing REST endpoints remain; provenance fields and run/history endpoints are additive. Model weights, database backup and synthetic verification logs remain in ignored local directories.
