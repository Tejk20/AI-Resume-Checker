# API reference

Local base: `http://127.0.0.1:8000/api/v1`. Live base: `https://avom-resume-checker.onrender.com/api/v1`. JSON payloads use snake_case. IDs are UUIDs. Swagger at `/docs` exposes generated Pydantic schemas. Lists return `{items, total}`. Single resources return an object. Failures return `detail` (a validation array for 422).

Hosted writes require an authenticated `avom_session` cookie. Private jobs and nested candidates, batches, rankings and history are scoped to the signed-in owner. Public sample jobs are readable without login and read-only for everyone. Unauthorized access to another account's private IDs returns 404. Dashboard totals include visible sample jobs and the current account's private jobs. Local compatibility mode can disable mandatory login through `AUTH_REQUIRED=false`.

| Method | Path | Request / response |
|---|---|---|
| GET | `/health` | 200 database connected, or 503 unavailable; model name and lazy-load policy |
| POST | `/auth/signup` | `{name,email,password}`; 201 user summary and session cookie; password 10–128 characters |
| POST | `/auth/login` | `{email,password}`; 200 user summary and session cookie |
| GET | `/auth/me` | `{user,auth_required}`; user is null without a valid session |
| POST | `/auth/logout` | 204; revoke session and clear cookie |
| POST | `/auth/forgot-password` | `{email}`; generic 202; 503 if sender/key is not configured |
| POST | `/auth/reset-password` | `{token,password}`; update password/revoke sessions; 400 for expired/used/invalid token |
| GET | `/dashboard` | Saved jobs, parsed resumes, evaluated pairs, mean score, distribution and recent batches |
| POST | `/jobs` | JSON `{title, raw_text}`; title 2–200 chars, text 30–100000; 201 extracted saved job |
| POST | `/jobs/upload` | Multipart `title`, `file` PDF/DOCX; 201 saved job |
| GET | `/jobs` | `offset=0&limit=50` (1–100); newest first |
| GET | `/jobs/{job_id}` | Reviewed/extracted requirements, raw JD, matching status/error |
| POST | `/jobs/{job_id}/copy` | 201 new private job using the visible source's requirements; sample candidates/results are not copied |
| PATCH | `/jobs/{job_id}` | Any requirement fields below; 200 updated job; clears stale match results |
| POST | `/jobs/{job_id}/resumes` | Multipart repeated `files`; 1–50; 202 batch |
| GET | `/batches/{batch_id}` | Status, total_files, processed_files (successes), failed_files, errors, timestamps |
| GET | `/jobs/{job_id}/candidates` | `offset`, `limit`; summaries omit contacts and raw text |
| GET | `/candidates/{candidate_id}` | Detailed extracted profile including contact fields, employment, projects, original filename |
| POST | `/jobs/{job_id}/match` | No body; 202 `{job_id,run_id,status:"processing"}` |
| GET | `/jobs/{job_id}/rankings` | `search`, `min_score` 0–100, `sort=score\|experience`, `offset`, `limit`; persisted results |
| GET | `/jobs/{job_id}/matches/{candidate_id}` | Scores, explanation, algorithm/model identifiers, run ID, scoring configuration and candidate summary |
| GET | `/jobs/{job_id}/matches/{candidate_id}/history` | Previous snapshots; offset and limit (default 20, max 100) |
| GET | `/jobs/{job_id}/runs` | Recorded run status/model/configuration; offset and limit (default 50, max 100) |

PATCH fields: `required_skills`, `preferred_skills`, `min_experience` (0–60 or null), `qualifications`, `responsibilities`. Empty lists remove requirements; lists cannot be null. Required/preferred sets must be disjoint. Lists support at most 100 entries, each at most 2000 characters. Updates are rejected while the selected job processes. Lists are trimmed and deduplicated. Add aliases to the taxonomy if introducing new canonical skills.

Example create:

```json
{"title":"Python Backend Developer","raw_text":"Python Backend Developer with at least 3 years of experience. Required Python, FastAPI and PostgreSQL. Build reliable backend APIs. AWS preferred."}
```

Batch status: `pending` → `processing` → `completed`, `partially_completed`, or `failed`. `processed_files + failed_files` is the number finished, not `processed_files` alone. Validate extensions and size before staging; content and extraction checks occur per file in the worker. Failures are batch error records. Accepted successful documents persist as candidates plus file metadata. Invalid documents do not create invented candidate records.

Match status lives on the job: `idle`, `processing`, `completed`, `failed`. Poll GET job until processing ends. Model/download failures set a safe error message. Polling errors in the frontend are visible and retryable. A matched job can be matched again; its result pairs update atomically after the previous versions are archived. After new uploads, rerun matching to include them. No default or fabricated scores appear while waiting.

Errors: 401 login required/incorrect credentials; 403 read-only sample or rejected origin; 404 missing/inaccessible resource; 422 validation or no candidates to match; 409 duplicate email or current job upload/match conflict; 429 account-attempt limit; 503 bounded worker/hash admission full; 500 generic internal failure. Do not return raw tracebacks, file paths or credentials. CORS is configured using a JSON array of permitted frontend origins.

There is intentionally no upload download/static route. Original filenames are safe basenames; file paths and resume text are not exposed in summary/detail schemas. Account identity and ownership checks are implemented; email verification/recovery, retention, reverse-proxy request limits and hardened document processing remain further production work. See [the complete project guide](../PROJECT_DOCUMENTATION.md) for all configuration and account details.
