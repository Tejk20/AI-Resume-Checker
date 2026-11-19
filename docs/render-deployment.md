# GitHub to Render and Neon (no-card free demo)

This deployment uses Render's Free web service for React + FastAPI and Neon's Free PostgreSQL plan for persistent application records. GitHub remains the source repository. No billing upgrade is configured. Both accounts must be authorized by the owner before provisioning; no live deployment is implied by committing these files.

## Smaller MPNet runtime

`Dockerfile.render` uses the official `all-mpnet-base-v2` quantized ONNX export, attention-mask mean pooling, normalized 768-dimensional embeddings and the existing section-aware scoring pipeline. The 25/40/25/10 formula is unchanged. Quantization is approximate: scores can differ slightly from the default float32 PyTorch runtime. Each result records `embedding_backend=onnx-int8`, precision and the pinned model revision. The ordinary Dockerfile and local default still use PyTorch MPNet.

The model revision and weight checksum are pinned in `scripts/download_onnx_model.py`; no candidate text is sent to an AI API. The runtime omits PyTorch and Sentence Transformers, processes one passage at a time, and retains at most 4 MiB of embedding cache. The `Free host memory checks` GitHub workflow tests the real 12-resume/three-job API workflow with the app container capped at 512 MiB and swap disabled. Check the actual workflow result before deploying; no memory-fit guarantee is inferred from the smaller weight file alone.

## Connect and deploy

1. Create/sign in to a [Neon Free account](https://console.neon.tech). Create a dedicated PostgreSQL project/database for this app. Use its connection string with SSL enabled. Keep it in a provider secret, never a GitHub commit or chat message.
2. Create/sign in to a [Render account](https://dashboard.render.com). When authorizing GitHub, choose **Only select repositories → Tejk20/AI-Resume-Checker**. Do not authorize Snatcho-Labs or unrelated repositories.
3. Once `Free host memory checks` passes, use [Deploy to Render](https://render.com/deploy?repo=https://github.com/Tejk20/AI-Resume-Checker). The repository's `render.yaml` selects the **Free** plan and `Dockerfile.render`; it does not create a Render Postgres database.
4. Enter the Neon connection string into Render's `DATABASE_URL` secret field. Review the service plan remains **Free** and deploy. Startup applies Alembic migrations automatically.
5. Open the actual `onrender.com` URL returned by Render. Verify `/api/v1/health`, create a synthetic job, upload the supplied 12 resumes and run matching. Test a second job too. Never guess a live service URL from its requested name.
6. Subsequent GitHub pushes deploy after checks pass. Review the deployment logs and health status on Render after changes.

## Practical limits

Render's Free service sleeps after idle periods and wakes on a request; it is not always-on hosting. CPU is limited, so matching can take longer than in Codespaces. Free-plan quotas apply at both providers. Without payment details, do not upgrade plans to remove these limits.

Neon stores extracted candidate text, job descriptions, match evidence and results across app restarts, within its free storage/compute allowance. Uploaded original PDF/DOCX files are on Render's ephemeral filesystem and are lost on restart/redeploy; the current app exposes no original-file download feature and matching uses the saved extracted records. Durable original-file retention needs external object storage.

## Accounts and populated sample workspace

The hosted image enables `AUTH_REQUIRED=true`, `SECURE_COOKIES=true` and `SEED_DEMO_DATA=true`. The Blueprint records the same values. `/signup` and `/login` create/use real database-backed accounts. Sessions expire after seven days and logout revokes the session. No tokens are kept in browser local storage. Account-owned jobs and their batches, candidates, matching runs and dashboard totals are scoped to that account. Email verification and password recovery are not yet available.

On startup the app creates three deterministic sample jobs and parses the 12 supplied fictional resumes under each, then computes genuine MPNet scores through the existing worker. The 36 candidate evaluations are visible without login, clearly labeled as sample data and read-only, and remain visible alongside each recruiter's own jobs. Repeated starts skip already evaluated sample jobs. Existing jobs/results are not overwritten or assigned to a newly created account; pre-account unowned records remain stored but are hidden in hosted account mode. The seeded overview refreshes while initialization is in progress.

These changes still support synthetic demonstrations only; document retention, email verification, account recovery and production operational controls need further work before handling real candidate records.

References: [Render free limits](https://render.com/docs/free), [Render first deploy](https://render.com/docs/your-first-deploy), [Neon pricing](https://neon.com/pricing), [official MPNet ONNX weights](https://huggingface.co/sentence-transformers/all-mpnet-base-v2/tree/main/onnx), [Sentence Transformers ONNX pooling guidance](https://sbert.net/docs/sentence_transformer/usage/efficiency.html).
