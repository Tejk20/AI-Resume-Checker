# Avom · Resume Intelligence

A local AI resume matching application for the Avom Consultants internship assignment. Recruiters create a job, review extracted requirements, upload a mixed PDF/DOCX batch, and inspect persisted, explainable candidate rankings. Every demonstration identity is fictional.

The problem: keyword counts alone miss similar experience and conceal why candidates rank differently. This application separates semantic evidence, exact skill coverage, relevant dated employment, and qualifications. Its compatibility score is a heuristic against a JD, **not a hiring probability or an objective assessment of a person**.

## Features

- Recruiter signup, login and logout with hashed passwords, expiring browser sessions and account-owned jobs. Hosted write access requires login; sample jobs remain publicly readable and cannot be modified.
- An idempotent sample workspace with three roles, 36 parsed synthetic resumes and genuine matching results. Hosted startup seeds missing samples in the background without replacing recruiter data.

- Six responsive React views: overview, create/review job, bulk uploads, filtered rankings, candidate analysis, About the application.
- PDF and DOCX parsing, 1–50 documents per batch, 10 MB default per file, partial failures and progress polling.
- Phrase-aware skill taxonomy with aliases and related skills; related skills receive no exact-match credit.
- Local `sentence-transformers/all-mpnet-base-v2` embeddings, section-aware retrieval, tokenizer-bounded chunks, model-specific vector caching; MiniLM remains a selectable baseline.
- Explainable scores with normalized weights, unrounded contributions, relevant employment evidence, uncertainty warnings, algorithm version.
- PostgreSQL JSONB persistence, UUIDs, foreign keys, unique current job/candidate results, versioned matching runs and retained result history; additive Alembic migrations preserve existing data.
- Bounded background executor; duplicate file hashes per job; interrupted-operation recovery on restart.
- 12 synthetic resumes (6 PDF, 6 DOCX), 3 JDs, real-model backend tests, frontend interaction tests and a real-model HTTP workflow verifier.

## Stack and architecture

React / Vite / JSX / Tailwind / React Router / Axios / Lucide / Recharts / React Hot Toast. Python 3.11+ / FastAPI / Pydantic / SQLAlchemy 2.x / Alembic / PostgreSQL / psycopg. Sentence Transformers / NumPy / scikit-learn / spaCy. PyMuPDF / python-docx.

```mermaid
flowchart LR
    UI[React recruiter workspace] --> API[FastAPI validation /api/v1]
    API --> PG[(PostgreSQL / JSONB)]
    API --> Queue[Bounded local worker]
    Queue --> Parse[PDF / DOCX extraction]
    Parse --> Profile[Skills / sections / employment]
    Profile --> AI[Cached MPNet embeddings]
    AI --> Score[Weighted scoring + evidence]
    Score --> PG
    Parse --> Files[Private file storage]
    PG --> API
```

## Project structure

```text
backend/app/api/routes.py          REST routes and pagination
backend/app/core/                 Settings, database, scoring weights
backend/app/models/entities.py    Seven relational ORM models including runs/history
backend/app/schemas/contracts.py  Pydantic API contracts
backend/app/services/             Documents, extraction, skills, semantic, scoring, workers
backend/app/data/                 Skill taxonomy JSON
backend/alembic/versions/         Committed initial schema migration
backend/tests/                    Parser, scoring and migration-backed API tests
frontend/src/pages/               Six connected application views
frontend/src/components/          Shared feedback, chips and score components
frontend/src/services/api.js      Central Axios client
sample_data/                     Fictional resumes and three JDs
scripts/                         Sample generation, model download, real HTTP verification
docs/                            Architecture, algorithm, API, demo/interview guide
```

## Prerequisites

Python 3.11 or 3.12, Node **22 LTS or 24 LTS** with npm, Git, and Docker Desktop or PostgreSQL 16+. Internet is needed for dependency installation and the initial model weights (approximately 420 MB for MPNet; approximately 90 MB for the MiniLM baseline). Inference runs locally afterward. No API keys or paid services are required. Allow several GB for PyTorch and dependencies. A CPU is sufficient for the supplied batch.

## Setup (PowerShell, from this project directory)

```powershell
docker compose up -d db
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

The supplied Docker database binds **127.0.0.1:5433** to avoid an existing installation on 5432. User `resume`, password `resume_local`, database `resume_matcher`. These are local demo credentials; change them for any deployment. `.env` files and runtime data are ignored by Git.

For an existing PostgreSQL server, create a dedicated database and user yourself, then change `DATABASE_URL` in `backend/.env`. Do not point the application at an unrelated database. SQLite is supported **only for isolated tests**, and is not the deployment default.

Optional Windows fallback when Docker is unavailable:

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py start
```

This helper downloads an official PostgreSQL **16.4** binary archive into ignored `storage/postgres`, initializes a separate cluster, and listens only on 127.0.0.1:5433. It uses loopback trust authentication for synthetic local testing. It never reuses the machine's existing data directory. Prefer current patched PostgreSQL through Docker for ongoing use; this compatibility helper is not production deployment infrastructure. Stop it with `python scripts/local_postgres.py stop` using the project interpreter.

Install the optional spaCy English pipeline:

```powershell
.\.venv\Scripts\python.exe -m spacy download en_core_web_sm
```

If that model is absent, the app explicitly uses `spacy.blank('en')` plus its sentence splitter; skill and date extraction remain deterministic. No NER model invents candidate fields.

Download the embedding model once:

```powershell
.\.venv\Scripts\python.exe scripts/download_model.py
```

The script loads the real model, embeds two sentences and prints a measured cosine similarity. It caches under `.model-cache/`. A first matching request can download the same model lazily. If the download fails, matching is marked failed with a retry message; no fake fallback scores are generated. `HF_HUB_OFFLINE=1` may be set after downloading to require offline inference.

## Run the application

For the GitHub-based full-app demo, see [deployment instructions](docs/deployment.md). The repository includes a CPU-only Docker image, private PostgreSQL service, same-origin React/API serving and a Codespaces configuration. Codespaces is a quota-limited demo environment rather than permanent hosting; launching it requires available free allowance and a $0 spending limit. No paid resource is provisioned by the repository.

Terminal 1:

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2, from the project directory:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open **http://127.0.0.1:5173**. Swagger: **http://127.0.0.1:8000/docs**. Health: **http://127.0.0.1:8000/api/v1/health**. `npm.cmd` avoids PowerShell's script execution policy for npm.ps1. On macOS/Linux use `.venv/bin/python` and `npm` instead.

Use **one API process**. Do not set `--workers` above 1: the in-process queue and restart recovery intentionally support one local demo process. Development `--reload` is possible, but interrupts active batches.

## Environment variables

| Variable | Default / purpose |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://resume:resume_local@127.0.0.1:5433/resume_matcher` |
| `CORS_ORIGINS` | JSON array of localhost frontend origins; no wildcard |
| `UPLOAD_DIR` | `storage/uploads`, relative to backend working directory; private files |
| `MAX_FILE_MB` | 10; both upload and parser enforce it |
| `MAX_BATCH_FILES` | 50 |
| `EMBEDDING_MODEL` | `sentence-transformers/all-mpnet-base-v2`; set to `sentence-transformers/all-MiniLM-L6-v2` for the baseline |
| `MODEL_NAME` | Deprecated compatibility alias; `EMBEDDING_MODEL` takes precedence |
| `EMBEDDING_CACHE_MB` | 128; bounded in-memory vector cache, zero disables retention |
| `EMBEDDING_BATCH_SIZE` | 32; lower for machines with limited RAM |
| `SCORING_WEIGHTS` | JSON object: semantic .25, skill .40, experience .25, education .10; must sum to 1 |
| `MODEL_CACHE` | `../.model-cache`, relative to backend |
| `VITE_API_URL` | `http://127.0.0.1:8000/api/v1` |

Start backend commands in `backend/` so its `.env` and relative storage paths resolve consistently. Frontend uses a local system-font fallback if Google Fonts is unavailable; core functionality needs no online font service.

## Workflow and scoring

The **Active job** selector supports search, common title suggestions and arbitrary custom titles. Choose a suggested/custom **Create** entry to open a prefilled Job Description form; saving the JD makes it available as an active job. Saved titles refresh when navigating or returning to the app. AI, AI Engineer, ML Engineer and AI/ML Engineer naming variants appear under one **AI/ML Engineer** role. When a role has several saved JDs, **Saved description** selects the actual job record and its own candidates/results; grouping does not combine or delete evaluations.

1. Create Job accepts pasted text or a JD PDF/DOCX. Extraction creates a saved job.
2. Review comma-separated skill lists, optional years and one-line qualifications/responsibilities. Save corrections. Requirement changes archive and invalidate current results, requiring rematching.
3. Upload files for the selected job. Poll batch status; each success persists a candidate and original file metadata. Per-file errors stay on the batch.
4. Run matching. A cached CPU model produces embeddings; each JD passage selects its most similar eligible resume passage. Responsibilities, skills, qualifications and role context are aggregated separately. Mandatory skills and years still use explicit evidence checks.
5. Open rankings, search by name, filter minimum score, sort by score or relevant years, and open detailed analysis. Refresh uses persisted API data.

Default formula: **0.25 semantic + 0.40 skill + 0.25 experience + 0.10 education**.

For scores 80, 90, 75, 100: `20 + 36 + 18.75 + 10 = 84.75`.

If experience and education requirements are absent, semantic and skill weights become approximately 38.46% and 61.54%, respectively. Unknown candidate experience stays applicable and receives an explicitly provisional 50 with manual review; it is never reported as confirmed experience. Unknown qualifications likewise receive 50 and a review warning. See [the reproducible algorithm specification](docs/matching-algorithm.md) for exact rules and limitations.

## API

All routes use `/api/v1`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health`, `/dashboard` | Health and persisted summary aggregates |
| POST / GET | `/jobs` | Create from text / paginated list |
| POST | `/jobs/upload` | Create from JD file |
| GET / PATCH | `/jobs/{id}` | Retrieve / correct requirements |
| POST | `/jobs/{id}/resumes` | Multipart batch; returns 202 |
| GET | `/batches/{id}` | Counts, status, per-file errors |
| GET | `/jobs/{id}/candidates` | Paginated summary without contacts |
| GET | `/candidates/{id}` | Detailed profile with contacts |
| POST | `/jobs/{id}/match` | Start asynchronous evaluation; 202 |
| GET | `/jobs/{id}/rankings` | Sorted/filtered paginated results |
| GET | `/jobs/{id}/matches/{candidate}` | Detailed explanation, model identifier, run ID and scoring configuration |
| GET | `/jobs/{id}/matches/{candidate}/history` | Previous evaluation snapshots |
| GET | `/jobs/{id}/runs` | Matching run configuration, status and provenance |

See [API reference](docs/api-documentation.md) and interactive Swagger request/response schemas.

## Tests and verification

```powershell
.\.venv\Scripts\python.exe scripts/generate_samples.py
cd backend
..\.venv\Scripts\python.exe -m pytest -q
cd ../frontend
npm.cmd test
npm.cmd run build
npm.cmd audit
cd ..
# Requires a running migrated backend and downloaded real model:
.\.venv\Scripts\python.exe scripts/verify_workflow.py
```

Unit/API tests use temporary SQLite databases **through the committed Alembic migration**. They verify aliases, false-positive boundaries, valid/corrupt/empty documents, overlapping dates, unknown evidence, score arithmetic, partial 13-file batches, missing resources and UUID validation. The separate verifier exercises real HTTP endpoints, the configured database and genuine embeddings with all 12 documents under all 3 JDs. It verifies evidence, weight/contribution reconciliation, distinct top candidates and persistence across fresh clients; results go to ignored `test-artifacts/workflow-report.json`.

See [verification results](docs/verification.md) for what actually ran in this workspace. Test outcomes are not inferred from source code.

## Screenshots

The local UI can be captured after running the demo. Any screenshots generated during verification live in `docs/screenshots/`. Do not include screenshots containing real applicant information. No mocked ranking rows are used to populate screenshots.

## Limitations and security

- Hosted accounts use PBKDF2-SHA256 password hashes (600,000 iterations), random server-side sessions, HttpOnly/Secure/SameSite cookies and job ownership checks across jobs, resumes, batches, rankings, history and dashboard totals. `AUTH_REQUIRED=true` enables mandatory signup/login for writes; local compatibility mode defaults to false. `SEED_DEMO_DATA=true` creates only the fictional read-only workspace. Email verification, password recovery, retention/deletion processes and production audit logging are not implemented. **Use synthetic data for this demonstration.**
- Rule-based extraction is conservative and English-focused. Ambiguous names return null. Dates need recognizable ranges in an employment section. Employer extraction is best-effort; unfamiliar layouts require review. Scanned PDFs need external OCR and fail clearly.
- Experience relevance is a skill-evidence rule, not an LLM judgment or proof of proficiency. It excludes internships and projects and merges overlapping month intervals. Year-only dates are approximate. Claims and negated skills are not fully understood.
- Qualification matching uses degree level and a limited subject check. Certification equivalence and nuanced alternative requirements are not automatically proven and may receive 50 with review. Education is never prestige-weighted.
- Neither MPNet nor MiniLM is recruitment-calibrated and may exhibit bias. Explicit English demographic/contact lines are filtered from score evidence, but implicit cues and unusual layouts are not guaranteed to be removed. Evidence retrieval can overvalue generic or repetitive descriptions. Scores are not probabilities; human review is mandatory.
- Background queue: one worker, five accepted operations, no distributed durability. On restart unfinished batches are marked failed/partial; retry remaining resumes. Pending files may remain in private storage and require local cleanup under your retention policy. Matching commits atomically; failures preserve the previous result set and expose failed status.
- File validation checks magic bytes and DOCX structure, 100-page PDF and expanded DOCX limits, UUID storage filenames, no public file route, and no code execution. It is not malware scanning or parser sandboxing. Run untrusted documents in a hardened environment before production.
- Duplicate hashes prevent reprocessing the same file within a job. A reformatted copy may evade hash detection. Sequential processing is intentionally conservative.
- Dashboard evaluation count refers to saved **job/candidate pairs**, not globally deduplicated people. Resume count refers to successfully parsed records. Upload/match status is durable, while the task queue is in memory.

Future improvements: email verification and account recovery, reviewed candidate field correction, stronger certification/subject extraction, OCR, durable task queue, upload request idempotency keys, retention/deletion workflows, calibrated relevance benchmarking, and fairness audits with representative consented data.

## Demo and interview preparation

### MPNet upgrade and model selection

The default is `sentence-transformers/all-mpnet-base-v2` on CPU. MPNet supplies 768-dimensional sentence vectors; MiniLM remains a selectable 384-dimensional baseline. MPNet was selected for evaluation of semantic matching, **not because larger models are automatically more accurate**. See [the measured comparison](docs/model-comparison.md) for all 12 candidates under three JDs, including rank/semantic differences, timings and sampled process memory. Recruiter-reviewed relevance labels are needed to measure ranking quality.

To download both models and choose the running model (PowerShell, project root):

```powershell
.\.venv\Scripts\python.exe scripts/download_model.py
.\.venv\Scripts\python.exe scripts/download_model.py --model sentence-transformers/all-MiniLM-L6-v2
# Set this in the terminal used to start FastAPI; restart after switching:
$env:EMBEDDING_MODEL='sentence-transformers/all-mpnet-base-v2'
# Baseline alternative:
# $env:EMBEDDING_MODEL='sentence-transformers/all-MiniLM-L6-v2'
```

The same `EMBEDDING_MODEL` setting can be stored in `backend/.env`. There is no silent automatic fallback: failure leaves existing results intact and records a failed run; explicitly select MiniLM if needed. Switching models does not relabel previously saved results. Run matching again to produce embeddings/scores for the chosen model. A changed model/revision/input limit/pipeline/cache directory/model instance clears incompatible in-memory vectors. MPNet accepts 384 tokens and MiniLM 256 including special tokens; long sentences use overlapping tokenizer-bounded chunks without dropping the tail. Section-aware comparison includes summary, technical skills, employment, projects, education and certifications. Similarity is never treated as proof of mandatory skills, certifications or professional years.

Every new result stores its actual model ID, algorithm version, matching run ID and scoring configuration. Previous scores/evidence are archived before a result is replaced or requirements invalidate it. Candidate analysis shows the model, formula, effective contributions, missing mandatory skills, separate uncertain requirements, section-labelled evidence and previous evaluations. The migration preserves existing rows and marks inferred/unknown legacy provenance explicitly. The current score is an **estimated job-fit score, not a hiring probability**; the application does not automatically reject candidates.

Additional upgrade checks (from project root; PostgreSQL running and both models downloaded):

```powershell
cd backend
$env:HF_HUB_OFFLINE='1'
$env:RUN_MODEL_TESTS='1'
..\.venv\Scripts\python.exe -m pytest -q
cd ..
.\.venv\Scripts\python.exe scripts/compare_models.py
.\.venv\Scripts\python.exe scripts/verify_mpnet_upgrade.py
```

The real-model suite currently has **45 passing backend tests** (ordinary offline unit runs skip two opt-in real-model cases), including hosted SPA/API boundaries and provider PostgreSQL URL handling. The frontend has **nine passing tests**, including grouped job selection, keyboard search, arbitrary title creation and prefilled forms. The upgrade verifier creates a separate, uniquely named PostgreSQL database using only the synthetic samples. It starts/stops its own test API processes, checks MiniLM history, rematches twice with MPNet and verifies persistence after an OS-process restart. It preserves the live application's records. Reports/logs go to ignored `test-artifacts/`. Optional `psutil` enables memory sampling in the comparison script; unavailable memory measurements are explicitly null. `scripts/rematch_saved_jobs.py` refreshes live saved jobs without uploading duplicates and checks that previous scores were archived.

Follow [the demo guide](docs/demo-guide.md) for a step-by-step presentation and interview answers. [Architecture](docs/architecture.md) explains boundaries and concurrency. [Matching algorithm](docs/matching-algorithm.md) lets you reproduce a score manually.

Model documentation: [MPNet model card](https://huggingface.co/sentence-transformers/all-mpnet-base-v2) and [MiniLM baseline](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). Documents are parsed locally, and contact details are only exposed on individual profile views. Do not commit `.env`, database files, model weights or private uploads.
