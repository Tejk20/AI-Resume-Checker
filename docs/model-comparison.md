# MiniLM and MPNet: measured comparison

Both models use algorithm 2.0.0, identical section-aware retrieval, the same 12 synthetic PDF/DOCX resumes, three JDs, and 25/40/25/10 scoring weights. This isolates the embedding-model change; it is not a comparison against the old unsectioned pipeline. No recruiter-reviewed relevance labels exist, so these measurements do **not** establish accuracy or hiring quality.

## Timing and memory

CPU only. Model weights were already cached locally. Fresh subprocess per model. Initialization includes library import and model load; matching excludes initialization. RSS is process memory sampled every 50 ms, not GPU memory or a guaranteed operating-system high-water mark. Timing and memory may vary with system load.

| Model | Dimensions | Input token limit | Initialization s | Total benchmark s | Sampled peak RSS MB | Peak increase MB |
|---|---:|---:|---:|---:|---:|---:|
| MiniLM | 384 | 256 | 27.7575 | 29.1939 | 580.94 | 314.72 |
| MPNet | 768 | 384 | 24.3676 | 30.0798 | 891.68 | 625.86 |

## Per-job results

Rank changes are descriptive differences, not validated improvements. Warm timings reuse cached vectors.

| Job | MiniLM first candidate / score | MPNet first candidate / score | MiniLM matching / warm s | MPNet matching / warm s | Candidates changing rank | Mean semantic change (MPNet - MiniLM) |
|---|---|---|---|---|---:|---:|
| ai_ml | Avery Reed / 90.71 | Avery Reed / 90.68 | 0.9891 / 0.0599 | 4.7384 / 0.0502 | 5 | +2.11 |
| python_backend | Alex Rowan / 90.05 | Alex Rowan / 90.41 | 0.0654 / 0.044 | 0.056 / 0.0406 | 2 | +2.62 |
| react_fullstack | Riley Fern / 92.51 | Riley Fern / 91.72 | 0.0908 / 0.0459 | 0.0624 / 0.039 | 0 | +2.02 |

## ai_ml: individual differences

| Candidate | MiniLM rank | MPNet rank | MiniLM semantic | MPNet semantic | Semantic change | MiniLM overall | MPNet overall |
|---|---:|---:|---:|---:|---:|---:|---:|
| Avery Reed | 1 | 1 | 62.85 | 62.72 | -0.13 | 90.71 | 90.68 |
| Quinn Lake | 2 | 2 | 46.1 | 51.04 | 4.94 | 66.53 | 67.76 |
| Cameron Moss | 3 | 3 | 39.18 | 39.41 | 0.23 | 60.8 | 60.85 |
| Finley Grey | 4 | 4 | 24.33 | 24.01 | -0.32 | 27.58 | 27.5 |
| Morgan Vale | 6 | 5 | 32.48 | 35.66 | 3.18 | 20.12 | 20.91 |
| Alex Rowan | 5 | 6 | 34.66 | 34.35 | -0.31 | 20.66 | 20.59 |
| Drew Elm | 7 | 7 | 24.23 | 31.61 | 7.38 | 14.06 | 15.9 |
| Casey Brook | 8 | 8 | 33.11 | 35.19 | 2.08 | 12.28 | 12.8 |
| Jordan Pine | 9 | 9 | 29.46 | 27.93 | -1.53 | 7.37 | 6.98 |
| Taylor Ash | 11 | 10 | 24.06 | 27.43 | 3.37 | 6.01 | 6.86 |
| Skyler Wren | 12 | 11 | 20.02 | 26.91 | 6.89 | 5.0 | 6.73 |
| Riley Fern | 10 | 12 | 26.11 | 25.69 | -0.42 | 6.53 | 6.42 |

## python_backend: individual differences

| Candidate | MiniLM rank | MPNet rank | MiniLM semantic | MPNet semantic | Semantic change | MiniLM overall | MPNet overall |
|---|---:|---:|---:|---:|---:|---:|---:|
| Alex Rowan | 1 | 1 | 60.21 | 61.63 | 1.42 | 90.05 | 90.41 |
| Morgan Vale | 2 | 2 | 61.07 | 58.19 | -2.88 | 82.27 | 81.55 |
| Casey Brook | 3 | 3 | 53.58 | 54.36 | 0.78 | 52.86 | 53.06 |
| Riley Fern | 4 | 4 | 50.88 | 48.28 | -2.6 | 35.52 | 34.87 |
| Avery Reed | 5 | 5 | 33.53 | 40.7 | 7.17 | 31.18 | 32.98 |
| Finley Grey | 6 | 6 | 25.61 | 30.49 | 4.88 | 30.3 | 31.52 |
| Drew Elm | 8 | 7 | 41.26 | 46.63 | 5.37 | 26.72 | 28.06 |
| Jordan Pine | 7 | 8 | 44.67 | 44.02 | -0.65 | 27.57 | 27.41 |
| Cameron Moss | 9 | 9 | 28.71 | 36.55 | 7.84 | 18.58 | 20.54 |
| Quinn Lake | 10 | 10 | 27.43 | 32.17 | 4.74 | 18.26 | 19.44 |
| Skyler Wren | 11 | 11 | 28.36 | 30.47 | 2.11 | 12.09 | 12.62 |
| Taylor Ash | 12 | 12 | 40.73 | 44.01 | 3.28 | 10.18 | 11.0 |

## react_fullstack: individual differences

| Candidate | MiniLM rank | MPNet rank | MiniLM semantic | MPNet semantic | Semantic change | MiniLM overall | MPNet overall |
|---|---:|---:|---:|---:|---:|---:|---:|
| Riley Fern | 1 | 1 | 70.03 | 66.88 | -3.15 | 92.51 | 91.72 |
| Jordan Pine | 2 | 2 | 63.4 | 62.59 | -0.81 | 82.85 | 82.65 |
| Taylor Ash | 3 | 3 | 53.5 | 56.19 | 2.69 | 47.21 | 47.88 |
| Alex Rowan | 4 | 4 | 51.33 | 53.78 | 2.45 | 32.17 | 32.78 |
| Finley Grey | 5 | 5 | 29.81 | 33.51 | 3.7 | 30.29 | 31.21 |
| Morgan Vale | 6 | 6 | 42.71 | 40.04 | -2.67 | 30.01 | 29.34 |
| Casey Brook | 7 | 7 | 49.55 | 52.11 | 2.56 | 27.72 | 28.36 |
| Skyler Wren | 8 | 8 | 32.78 | 36.27 | 3.49 | 23.86 | 24.73 |
| Drew Elm | 9 | 9 | 39.28 | 41.44 | 2.16 | 19.82 | 20.36 |
| Avery Reed | 10 | 10 | 31.16 | 37.65 | 6.49 | 17.79 | 19.41 |
| Cameron Moss | 11 | 11 | 29.28 | 34.47 | 5.19 | 12.32 | 13.62 |
| Quinn Lake | 12 | 12 | 28.3 | 30.39 | 2.09 | 12.07 | 12.6 |

## Regression checks and limitations

Both models returned bounded scores and deterministic warm-cache repeats. Mandatory missing-skill lists remained identical across models. MPNet is not assumed more accurate because it is larger. Meaningful accuracy evaluation needs recruiter-reviewed relevance judgments and a larger representative dataset. Model changes can raise or lower semantic scores; the compatibility scale is not calibrated as a probability. Full machine-readable outputs are in ignored test-artifacts/; this report contains only fictional identities.
