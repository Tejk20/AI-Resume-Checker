# Demonstration and interview preparation

## Before presenting

Use the README setup commands. Start PostgreSQL, apply `alembic upgrade head`, download MPNet, then start FastAPI and React. Visit `/api/v1/health` and `/docs`. Ensure the sample folder contains 12 resumes. Run backend tests, frontend tests and production build. Use only fictional sample documents.

## Suggested 10-minute walkthrough

1. Open the overview: metrics come from PostgreSQL aggregates, and an empty workspace has useful empty states.
2. Create a job titled Python Backend Developer. Paste `sample_data/job_descriptions/python_backend.txt`, or upload its PDF. Click Extract requirements.
3. Explain that extraction creates a saved job. Review required Python, FastAPI, PostgreSQL, REST API and Docker; AWS is preferred. Review 3 years and the qualification requirement. Make a small correction and save.
4. Open Upload resumes. Select all 12 documents in `sample_data/synthetic_resumes`. Show PDF and DOCX selection, sizes and batch counts. Explain the 50-file and 10 MB limits.
5. Upload; watch background processing. Finley has unknown experience and education rather than fabricated values. Optionally add a corrupted PDF to a separate batch to demonstrate graceful failure.
6. Run matching. Explain that the first model load can take longer, while polling keeps the UI responsive. No external paid API is called.
7. Open Candidate rankings. Backend-oriented candidates should generally lead this JD. Search, filter minimum score, and sort relevant experience. Scores remain on refresh.
8. Compare Alex or Morgan with Drew or Skyler. Open analysis. Show exact matched skills, required skills not identified, related technologies without exact credit, estimated relevant dates, and qualification evidence.
9. Show semantic evidence: each responsibility has an actual supporting resume passage. A cosine score expresses embedding alignment, not a skill certification or hiring likelihood.
10. Read the stored component scores and weights. Multiply each, add contributions, and round once. The default manual example 80/90/75/100 gives 84.75. If a JD omits education, show its redistributed weights.
11. Create the React and ML jobs, upload the same 12 fictional documents, and rematch. Riley/Jordan and Avery should rise for their relevant roles; rankings must depend on the JD. `scripts/verify_workflow.py` automates the real workflow and checks distinct leaders.
12. Demonstrate persistence by refreshing and revisiting the job, or restarting FastAPI after completion. Use a read-only database query to show `jobs`, `candidates` and `match_results` rows. Do not show raw personal data from other databases.
13. Open the source layers and tests. Explain a boundary test (Java ≠ JavaScript), overlapping dates, provisional unknown evidence, migration-backed API tests and the real-model verifier.

## Questions you should be able to answer

Before comparing models, download both with `scripts/download_model.py` (use `--model sentence-transformers/all-MiniLM-L6-v2` for the baseline). Set `EMBEDDING_MODEL` and restart FastAPI. Existing results retain their recorded model until rematched. On candidate analysis, show the embedding model, the 25/40/25/10 formula, section-labelled evidence, separate uncertainty and previous evaluation history. The About page remains an application/features overview.

Run `scripts/compare_models.py` to regenerate [the measured comparison](model-comparison.md). Explain the actual rank changes and execution/memory trade-offs, and explicitly distinguish them from measured accuracy: this dataset has no recruiter-reviewed relevance labels. Run `scripts/verify_mpnet_upgrade.py` for isolated PostgreSQL/history/restart verification. The additive migration must run before starting the upgraded backend.

**Why FastAPI?** Pydantic validates requests, typing documents contracts, Swagger makes endpoints inspectable, and Python hosts the NLP libraries directly. CPU-heavy embedding work runs in a bounded background thread, not the request coroutine.

**Why PostgreSQL?** Relational integrity ties jobs, batches, candidates and results together; JSONB stores flexible extraction/evidence lists. Unique constraints prevent duplicate result pairs. Alembic makes schema changes repeatable. SQLite tests do not replace real PostgreSQL verification.

**Why Sentence Transformers?** MPNet provides locally runnable pretrained sentence embeddings, so semantically similar descriptions can align even with different wording. MiniLM remains an explicit baseline for lower-resource machines. It needs a one-time model download, not an API key. It is not specifically calibrated for hiring.

**What is an embedding?** A vector representation of text learned from language data. MPNet emits 768 numbers; MiniLM emits 384. Nearby directions often represent related meanings, but the model does not establish truth or capability.

**What is cosine similarity?** Dot product divided by vector lengths; for unit-normalized vectors, just the dot product. We clamp cosine similarities to [0,1], select the strongest eligible resume passage per requirement, average within requirement groups, then combine responsibilities 50%, skills 20%, qualifications 15% and role context 15% (renormalized when absent), multiplying by 100. We do not apply a probability interpretation.

**Why chunk?** The transformer has a context limit. Tokenizer-bounded passages avoid silently losing later experience. Best evidence per requirement makes the result inspectable. It can still overvalue generic or repeated statements, so manual review matters.

**How are skills found?** A canonical taxonomy defines aliases. Escaped phrase boundaries and longest overlapping matches prevent accidental substring credit. Related technologies remain separate. Rule-based extraction cannot fully understand negation, and recruiters must review extracted JD requirements.

**How are years calculated?** Parse dated employment, turn boundaries into month indices, exclude internships, filter relevant roles by job skill evidence, merge overlapping intervals, divide by 12. Projects are evidence for semantics, not professional years. Year-only dates are approximate and flagged.

**How are unknowns handled?** Missing JD requirements remove a component and normalize weights. Missing candidate evidence retains that component with a provisional 50 and an explicit review warning. Unknown years stay null. This is a visible policy assumption and should be revised after validation, not disguised as extracted fact.

**How do explanations remain truthful?** They are generated from computed components, extracted skills, stored role evidence and actual retrieved passages. They say “not identified”, store algorithm version, and persist weights and contributions together with the result.

**What about protected characteristics?** Structured scoring does not use demographic fields or identity. Name/contact headers are excluded from normal semantic evidence. Unusual layouts and model bias still require review; this is not proof of fairness. Production requires a dedicated audit and robust content separation.

**How do uploads fail?** Size/extension checks precede staging. Signature/ZIP structure checks and parser errors produce per-file batch failures. Scanned PDFs report OCR required. Successes continue and persist. Random UUID storage filenames prevent filename traversal. No upload is executed or publicly served.

**What happens on a restart?** Saved records persist. The in-memory queue does not: startup marks unfinished batches failed/partial and interrupted matching failed. Retry unfinished files or rerun matching. Normal shutdown waits for accepted tasks. Run one API process.

**How would you scale?** Add authentication and tenant isolation, private object storage, durable worker jobs with idempotency, transactional job locks, embedding caches keyed by text/model version, representative retrieval/scoring benchmarks, bounded processing containers, and retention/audit policies. Do not claim the current thread executor is distributed infrastructure.

**What remains limited?** English extraction, unfamiliar layouts, nuanced certification equivalence, OCR, truthful claims, parsing confidence and model calibration. It assists review; it must not automatically reject candidates.
