# Verification record

## Current live deployment and accounts — 19 November 2026

This section supersedes earlier status statements about publication, Docker, authentication and hosting. The older entries below are retained as dated historical records.

- Live application: <https://avom-resume-checker.onrender.com>; signup at `/signup`.
- Source baseline: `08f2492`, recruiter accounts and populated read-only sample workspace.
- Latest full local backend suite: **49 passed, two optional real-model tests skipped**; frontend: **12 passed**, production build passed.
- [Updated free-host container check](https://github.com/Tejk20/AI-Resume-Checker/actions/runs/44551396602): **passed** with real ONNX MPNet, account/private-job workflow and public sample seeding under a hard 512 MiB/no-swap cap, without OOM or container restart.
- [Updated normal PyTorch container check](https://github.com/Tejk20/AI-Resume-Checker/actions/runs/44551396549): **passed** with real matching and PostgreSQL.
- Live anonymous overview: **3 jobs, 36 parsed resume records, 36 evaluations**, completed sample seed, average score **32.92** at verification. The same 12 fictional profiles appear under three roles.
- Live signup, Secure/HttpOnly/SameSite cookie, authenticated session, logout, signin again and logout: **passed** using one clearly synthetic QA account; no recruiter jobs modified.
- All three live sample rankings returned 12 candidates and ONNX provenance. Compiled signup route/JavaScript served successfully.
- Account tests cover duplicate/invalid signup, password hashing, expiry, ownership across direct/nested resource APIs, private dashboard totals, read-only samples, origin rejection and idempotent seed counts.
- Interactive visual browser QA remains unavailable; component/HTTP checks do not claim screenshot or viewport verification.

See [complete project documentation](../PROJECT_DOCUMENTATION.md) for current architecture, setup, scoring, API, deployment and limitations.

## Historical preparation and development records

## GitHub deployment preparation — 18 November 2026

- Local backend: **45 passed** with both real models and hosted SPA/API boundary tests.
- Frontend: **nine passed**; production build passed with same-origin API configuration.
- [GitHub Linux container checks](https://github.com/Tejk20/AI-Resume-Checker/actions/runs/44246490525): **passed**, including Docker build, PostgreSQL startup, frontend/API health and the real synthetic 12-resume/three-JD MPNet workflow.
- A Codespace/public app has **not** been launched yet: personal billing totals were unavailable through the current GitHub connection, and the existing CLI authorization lacks Codespaces access. The free-only condition requires confirmation of remaining allowance and a $0 spending cap before resource creation. No paid resource was created.

## Active job selector update — 18 November 2026

Frontend tests: **nine passed** across four files. Production build: **passed**. Verified that AI Engineer and AI/ML Engineer share one role option while both saved descriptions remain independently selectable; an arbitrary saved role is searchable; keyboard selection works; and an arbitrary new title opens the prefilled Create Job form. Common title suggestions are optional, not a restriction on supported jobs. The job list refreshes on navigation/window focus. Grouping is presentation-only: original job IDs, JDs, candidates, model results and histories are preserved. No backend/schema/data changes were made for this UI update. Browser visual QA remains unverified.

## MPNet upgrade — 18 November 2026

Current default: `sentence-transformers/all-mpnet-base-v2`, CPU, 768-dimensional normalized vectors, active 384-token limit. Algorithm: `2.0.0-section-aware`. Formula remains **25% Semantic + 40% Skills + 25% Relevant Experience + 10% Education**. Weights are configurable and validated to sum to 1.0.

| Check | Observed result |
|---|---|
| Real MPNet download/load | Loaded successfully on CPU from the project model cache |
| Backend tests | **43 passed**, including opt-in actual MPNet and MiniLM inference; four dependency/binding deprecation warnings |
| Semantic tests | Dimensions, unit norms, cosine similarity, complete long-text coverage, section selection, bounded scores, cache reuse/model invalidation and explicit model/inference failures passed |
| Scoring | 25/40/25/10 weights, manual 84.75 calculation, redistribution, missing mandatory skills and separate uncertainty passed |
| Frontend | **Five tests passed** across three files; model/formula/uncertainty/history display included |
| Production build | Passed after final candidate-analysis changes |
| Live database migration | Backup created before the additive migration; existing records retained; Alembic schema consistency check passed |
| Live application | Healthy MPNet backend; all **37 current saved results** rematched, each previous score checked in history |
| Isolated PostgreSQL workflow | Three sample JDs × 12 mixed PDF/DOCX resumes: **36 candidates, 36 unique current results, 72 history snapshots, nine runs** |
| Cross-model preservation | MiniLM results remained unchanged merely by selecting MPNet; explicit rematching archived prior MiniLM scores/configuration |
| Duplicate-free rematching | Each job matched once with MiniLM and twice with MPNet; current job/candidate pairs stayed at 36 |
| Restart persistence | Test API stopped and restarted as a new OS process; all 36 MPNet scores persisted exactly |
| Failure behavior | A failed rematch preserved prior results; a failed run and safe error were recorded |
| Run traceability | Model/configuration/run ID stored; accepted runs recorded before queue submission; queued/interrupted status recovery retained |
| Private artifacts | Model cache, database backup and test artifacts confirmed ignored by Git |
| Existing saved-results verifier | Passed against current rankings and archived MiniLM reference scores, including additional user-created jobs/candidates |
| Publication | No GitHub publishing performed |

The full PostgreSQL/HTTP test was repeated after the final queue/run-record change and passed again. Temporary API processes were stopped by the verifier; its separate synthetic PostgreSQL database is retained for inspection. The live application's original job/candidate records were preserved. The live backup is `storage/backups/before-mpnet-upgrade.dump` (ignored). Matching history is stored transactionally before current results are replaced or invalidated.

### Measured comparison

Both models used identical section-aware preprocessing and scoring, 12 synthetic resumes and three JDs. This compares model effects within the new pipeline, not the old unsectioned MiniLM pipeline.

| Measurement | MiniLM | MPNet |
|---|---:|---:|
| Dimensions | 384 | 768 |
| Active token limit, including special tokens | 256 | 384 |
| Initial library/model/JD preparation (seconds) | 27.7575 | 24.3676 |
| First 12-resume batch, AI/ML JD (seconds; excludes initialization) | 0.9891 | 4.7384 |
| Three-JD benchmark total, including initialization (seconds) | 29.1939 | 30.0798 |
| Sampled peak process RSS (MB) | 580.94 | 891.68 |

MPNet changed five candidate rank positions for the AI/ML JD and two for the Python JD; React rank positions were unchanged. The same leading synthetic profiles remained first. Mean semantic changes (MPNet minus MiniLM) were +2.11, +2.62 and +2.02 points for AI/ML, Python and React respectively. These are descriptive changes, **not evidence of improved accuracy**. The single-run CPU/RSS measurements vary with system load and include host-library overhead; RSS was sampled every 50 ms, not measured as an exact OS high-water mark.

See [all per-candidate differences and benchmark details](model-comparison.md). Recruiter-reviewed relevance labels and a larger representative dataset are needed to measure accuracy. No automatic rejection threshold was added.

### Reproduction

From project root, with PostgreSQL and both cached models available:

```powershell
cd backend
$env:HF_HUB_OFFLINE='1'
$env:RUN_MODEL_TESTS='1'
..\.venv\Scripts\python.exe -m pytest -q
cd ../frontend
npm.cmd test
npm.cmd run build
cd ..
.\.venv\Scripts\python.exe scripts/compare_models.py
.\.venv\Scripts\python.exe scripts/verify_mpnet_upgrade.py
```

Machine-readable outputs: `test-artifacts/minilm-comparison.json`, `mpnet-comparison.json`, `model-differences.json`, and `mpnet-integration-report.json`. These contain only synthetic evaluation data. The isolated verifier requires permission to create a database; the supplied local PostgreSQL/Docker setup grants it.

### Checks not executed / remaining limits

- Interactive browser QA and screenshots remain unavailable: the Browser runtime reported no available browser. UI interaction tests, production compilation and HTTP serving were verified instead.
- Docker itself was not installed or run; actual PostgreSQL 16.4 was used through the existing local compatibility helper.
- Optional spaCy `en_core_web_sm` remains absent; the tested pipeline uses the English sentencizer fallback plus deterministic extraction.
- The host has Node 23.7.0; build/tests passed, but Node 22 or 24 LTS is recommended for the tools' supported engines.
- Recruitment accuracy/fairness is unmeasured without reviewed relevance labels. English section extraction, degree/certification rules and demographic filtering are conservative; explicit requirements still need human review.
- MPNet uses more RAM and more first-batch inference time than MiniLM in the measured run. The in-memory cache/worker supports one backend process; neither task queues nor embeddings are distributed.
- The existing local-demo authentication, OCR and production-hardening limitations remain. No real applicant data is included in the benchmark or isolated verification.

## Historical verification before the MPNet upgrade

The following earlier record is retained for traceability. Its MiniLM versions, historical scores and old test counts are superseded by the current verification above.

Executed locally on 17 November 2026. This record distinguishes source implementation from observed execution.

## Scoring-policy update: version 1.1.0

The current formula is **Match Score = 0.25S + 0.40K + 0.25E + 0.10Q**: semantic similarity 25%, skill matching 40%, relevant experience 25%, qualifications 10%. All 32 backend tests passed after this change, including the revised manual calculation (84.75 for components 80/90/75/100) and redistribution checks. All 37 currently saved results were recalculated with version `1.1.0-minilm-evidence`; the extra result reflects application usage after the initial synthetic verification.

The integration counts and score table below record the original 36-result run under version 1.0.0; those historical scores are superseded by the current formula. Updated leaders are Alex Rowan 89.01 (Python backend), Riley Fern 92.17 (React full stack), and Avery Reed 90.88 (AI/ML).

## Implemented and verified

| Check | Observed result |
|---|---|
| Python dependencies | Installed in project `.venv`; initial inherited FastAPI/Starlette mismatch corrected |
| Backend automated tests | **32 passed**; extraction, documents, scoring, migration-backed API, partial 13-file batch, explicit demographic exclusion and unverified certification safeguards |
| Frontend tests | **4 passed** across two files; error states, score display, job context, create/correct/save interaction |
| Frontend production build | **Passed**; application, React and chart bundles split, no oversized-bundle warning |
| Frontend dependency audit | **0 vulnerabilities** after patched Vitest and explicit peer dependencies |
| Frontend local server | Vite started at `http://127.0.0.1:5173`; HTTP 200 |
| Database | Isolated PostgreSQL **16.4**, loopback port 5433; existing installation data untouched |
| Alembic migration | Initial schema applied successfully to PostgreSQL; five domain tables and version table observed |
| Migration consistency | `alembic current` reports head; `alembic check` reports no new upgrade operations |
| Backend startup | FastAPI/Uvicorn started at `http://127.0.0.1:8000`; health reported database connected |
| Genuine semantic model | MiniLM loaded from local cache; **384 dimensions**; measured test sentence cosine **0.5122** |
| Real HTTP integration | **3 jobs × 12 mixed PDF/DOCX resumes = 36 persisted match results** |
| Explanations | Semantic evidence present; component weights sum to 1; contributions reconcile with final score within final rounding |
| Rankings | Descending bounded 0–100 scores; different relevant profiles lead all three JDs |
| Private artifacts | Git ignores `.venv`, `node_modules`, uploads/database storage, model cache, `.env`, test artifacts |
| Actual server/database restart | All three saved rankings retained exactly the same leaders and scores after API and PostgreSQL restart |
| Persisted querying | Name/minimum-score filters, pagination and relevant-experience ordering passed; PostgreSQL stores explanation as JSONB; counts confirmed directly as 3 jobs / 36 candidates / 36 matches |
| Final-code rematching | Recomputed all three existing jobs with final privacy/qualification safeguards; leaders and scores unchanged and result count remained 36, confirming updates rather than duplicate results |

Synthetic integration leaders (not hardcoded UI data):

| JD | Highest-ranked synthetic candidate | Score |
|---|---|---:|
| Python backend | Alex Rowan | 84.62 |
| React full stack | Riley Fern | 89.05 |
| AI/ML | Avery Reed | 87.22 |

The machine-readable run output is in ignored `test-artifacts/workflow-report.json`. Rerun `scripts/verify_workflow.py` against a fresh migrated database to reproduce the workflow. It creates three more demo jobs if run again on an existing database.

## Verification limits

- **Interactive browser QA and screenshots were not executed.** The Browser skill runtime initialized, but reported no available browser connections (`[]`). UI component interaction tests, production compilation and HTTP serving passed; these do not prove visual appearance at every viewport or a complete browser-driven upload flow.
- Docker was not installed, so `docker compose up` was not executed. An isolated real PostgreSQL server was used instead. The Compose file is provided for normal setup.
- Optional `en_core_web_sm` was not installed. The tested parser uses spaCy's blank English sentencizer fallback plus deterministic extraction rules.
- The host had Node **23.7.0**. Build and tests passed, but patched Vitest's declared engines exclude this non-LTS version. Use Node **22 or 24 LTS** for a supported setup.
- Two backend deprecation warnings came from the host's inherited AnyIO pytest integration and Starlette's TestClient/httpx compatibility; tests passed. A fresh venv is recommended by the README.
- The portable compatibility database uses PostgreSQL 16.4 and loopback trust for fictional data. Use current patched PostgreSQL with proper authentication for any continued deployment.

## Remaining prototype limitations

OCR is optional and unimplemented; scanned documents fail clearly. Extraction of unfamiliar layouts, employer names and certification equivalence remains conservative. Professional experience relevance is an inspectable heuristic, not a verified employment claim. The worker queue is local and supports one API process. Authentication, authorization, retention/deletion workflows, production hardening and recruitment calibration are future work, not completed production features.
