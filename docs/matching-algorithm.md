# Reproducing the matching algorithm

Algorithm version: `2.0.0-section-aware`. The persisted explanation stores components, normalized weights, full-precision contributions, matched/missing lists, relevant roles, semantic evidence and uncertainty warnings. Scores are heuristic measurements of JD alignment. They are neither selection decisions nor probabilities.

## 1. Normalize explicit skills

The curated `backend/app/data/skill_taxonomy.json` defines canonical skills, valid aliases, and related technologies. Phrase boundaries prevent Java from matching JavaScript. Longest overlapping phrases take priority, so React Native is not also React. Aliases such as Python3 and Postgres map to Python and PostgreSQL. Context is needed for the JS alias. Related skills (e.g. Django supporting FastAPI) are evidence only, with zero exact-match credit.

JD sentences and preference clauses are classified using required/must/essential and preferred/bonus/nice-to-have wording, including section context. Recruiters review and correct the resulting lists. Unknown custom skills can be entered manually, but require a taxonomy addition to be automatically extracted from candidate documents. Negation, years per individual skill, and complex mixed clauses are extraction limitations.

Required coverage R = identified required skills / required skills. Preferred coverage P is analogous.

- Both sets present: `skills = 100 × (0.8R + 0.2P)`.
- Only one set present: `skills = 100 × coverage of that set`.
- Neither: skill component inapplicable.

Not identified means absence of extracted evidence; it does not prove a candidate lacks the skill.

## 2. Retrieve semantic evidence

The default model is `sentence-transformers/all-mpnet-base-v2` (CPU, 768 dimensions). Select `sentence-transformers/all-MiniLM-L6-v2` as the explicit baseline (384 dimensions). Set `EMBEDDING_MODEL` and restart the backend. A failed model load fails that run with a safe, retryable message; it never silently substitutes another model or fabricates a score.

The loaded Sentence Transformer reports its input limit: **384 tokens for MPNet** and **256 for MiniLM**, including special tokens. Reserve `tokenizer.num_special_tokens_to_add(pair=False)` slots, split each sentence into payload windows and overlap up to 32 tokens. Every token is covered, including the end of long documents. There is no old 300/60-chunk cutoff. spaCy provides sentence boundaries; structured section detection remains rule-based. The model weights are cached on disk; inference runs locally after download.

Explicit demographic/contact lines and known candidate identifiers are removed before scoring evidence is prepared. This is conservative English filtering, not exhaustive anonymization or proof of fairness.

Job requirement groups and weights inside the semantic component:

| Group | Weight | Eligible resume sections |
|---|---:|---|
| Responsibilities | .50 | Work experience, projects, summary |
| Required/preferred skill context | .20 | Technical skills, experience, projects, summary |
| Qualifications | .15 | Education, certifications |
| Role context | .15 | Summary, experience, projects |

Responsibilities use reviewed job responsibilities (or recognized JD summary when available); skills use the reviewed lists; qualifications use the reviewed requirements; role context uses the title. Absent groups are omitted and the remaining semantic-group weights normalized. If the expected resume sections are absent, search all available passages and explicitly flag `section_fallback` in evidence and a review warning. If no recognizable sections exist, use sanitized unstructured text. No resume passages means semantic score zero.

For L2-normalized embeddings, dot product equals cosine:

`cos(a,b) = dot(a,b) / (norm(a) × norm(b))`.

For each job passage, select the highest `clamp(cosine, 0, 1)` among eligible resume passages. Average these best values **within each requirement group**, then take the normalized weighted group mean and multiply by 100. Round the semantic component to two decimals before final weighting. Stored evidence contains both section labels, the selected texts, similarity and fallback status. Repeated chunks do not receive additive credit.

Example: group means responsibilities .8, skills .7, qualifications .9 and role .6 produce `100 × (.50×.8 + .20×.7 + .15×.9 + .15×.6) = 76.50`. This is textual alignment, not proof of a mandatory skill, certification or dated professional experience. Those components still use explicit evidence and uncertainty policies below.

The model is initialized once for the configured identifier/cache directory per process. Job vectors are reused for every candidate; uncached resume passages are deduplicated and embedded in a single batched preparation step. A bounded LRU cache (128 MB by default) stores vectors under hashed text keys, isolated by model identifier, revision, token limit, pipeline version, cache folder and loaded model instance. Changing that namespace clears incompatible vectors. Prepared candidate vectors also carry their namespace and are rejected if supplied to a different evaluation. The cache is process-local and cleared on restart; raw resume text is not used as cache keys.

## 3. Estimate relevant professional experience

Only dated roles inside detected employment sections count. Recognize month-name/year, MM/YYYY, YYYY, hyphen/en-dash/to ranges and Present/Current. Dates are month indices: `year × 12 + month - 1`. Durations are end-exclusive, e.g. Jan 2020 to Jan 2023 = 36 months. Present uses the machine's current month. Year-only dates use January and carry uncertainty warnings; invalid or future ranges are excluded.

Exclude roles marked Intern/Internship from professional years. Projects do not supply professional time. Merge overlapping intervals before dividing months by 12. Example Jan 2020–Jan 2023 plus Jan 2022–Jan 2024 = 4 years, not 5.

A role is relevant if its extracted skill set covers **at least one third** of the JD required skills (preferred skills if no required skills). With no skill requirements, inspect distinctive job-title word overlap. Merge only relevant professional intervals for relevant years. This conservative evidence rule is an estimate, not proof of proficiency. Roles with unrelated Java work must not become Python experience just because the overall resume lists Python.

`experience = 100 × min(1, relevant_years / required_years)`.

If no positive experience minimum is stated, the component is inapplicable. If candidate dates are unknown, use an explicitly **provisional 50** while retaining its weight, report unknown years and require manual review. This avoids treating missing evidence as either a confirmed failure or a nonexistent JD requirement. It is a policy assumption, not an inferred candidate fact. For a 4-year requirement, 3 reliably relevant years produce 75.

## 4. Compare qualifications

No explicit JD qualification means no education weight. Otherwise each requirement receives:

- 100 when the stated degree level is met or exceeded and the limited required subject check passes; an explicit accepted equivalent-experience clause can pass when reliable relevant years meet the JD minimum.
- 50 for unknown evidence, unverified certifications or potentially equivalent subject/degree information, with manual review.
- 0 when a clearly identified degree level is lower than the explicit requirement.

Average multiple requirement values. Levels are diploma/secondary (0), bachelor (1), master (2), doctorate (3). Subject rules recognize computer science, engineering and information technology broadly; they are intentionally limited and require review. Certification requirements are not auto-confirmed by a loose keyword. No prestige, age, gender, religion, nationality, image or identity score exists.

## 5. Combine components

Default weights in `app/core/config.py`: semantic .25, skill .40, experience .25, education .10.

**Match Score = 0.25S + 0.40K + 0.25E + 0.10Q**, where S is semantic similarity, K is skill matching, E is relevant experience, and Q is qualifications. All four component scores are measured from 0 to 100. Version 2.0 preserves the 25/40/25/10 policy introduced in version 1.1. Set `SCORING_WEIGHTS` to a JSON object with exactly these four component keys; finite nonnegative weights must sum to 1.0. A positive applicable weight is required. To change semantic models, run matching again; weight-only recalculation cannot generate MPNet embeddings.

For applicable set A: `effective_weight[k] = default_weight[k] / sum(default_weight[j] for j in A)`.

`contribution[k] = component[k] × effective_weight[k]`.

`overall = round(clamp(sum(contributions), 0, 100), 2)`.

Store unrounded contributions and effective weights so their sum reproduces the result to the final rounding step. The UI shows contributions to four decimals and percentages to two; display rounding can differ slightly from full-precision arithmetic.

Manual example with all requirements present:

| Component | Score | Weight | Points |
|---|---:|---:|---:|
| Semantic | 80 | .25 | 20 |
| Skills | 90 | .40 | 36 |
| Experience | 75 | .25 | 18.75 |
| Education | 100 | .10 | 10 |
| **Overall** | | **1** | **84.75** |

If experience and education requirements are absent, use .25/(.25+.40) for semantic and .40/(.25+.40) for skills: scores 80 and 90 yield **86.15**. If skills are also unspecified, semantic receives weight 1. Unknown candidate evidence remains applicable; never redistribute away its weight without a stated policy change and new algorithm version.

Sort stored results by descending overall score, then candidate UUID for stable ties. Optional experience sorting uses stored **relevant years**, never total years. Components and explanations are recomputed together, and a unique database constraint prevents duplicate result pairs.

## 6. Preserve model and scoring history

Each matching run stores its model identifier, resolved model revision when available, dimensionality, token limit, semantic pipeline configuration, default weights and algorithm version. Current results reference a run ID and retain normalized contributions. Before replacing a result or invalidating it after JD corrections, archive its full previous scores and evidence in `match_result_history` in the same transaction. The unique current job/candidate pair remains unchanged. A failed run preserves the previous current results. Legacy versions are marked as inferred MiniLM where their old algorithm identifier establishes that provenance; unrecognized historical models remain `legacy/unknown`, never relabeled MPNet. Historical configuration gaps are explicit. The optional weight-only utility records `2.0.0-reweight-only`, reuses and labels the original semantic model, and archives prior values.

See [the measured comparison](model-comparison.md) for MiniLM/MPNet ranking, runtime and memory differences on synthetic data. A larger model is not assumed to be more accurate; recruitment quality requires recruiter-reviewed relevance labels.
