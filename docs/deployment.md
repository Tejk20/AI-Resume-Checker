# GitHub-based demo deployment

This is a complete React + FastAPI + PostgreSQL deployment, with the existing CPU MPNet engine. GitHub Pages alone cannot run Python/PostgreSQL. The free 512 MB service tiers are below this application's measured MPNet memory usage. No model downgrade or paid resource is configured.

## What is prepared

- `Dockerfile` builds React and a CPU-only Python image, downloads MPNet at image-build time, and starts one FastAPI process after migrations.
- FastAPI serves the compiled React app and `/api/v1` on the same origin, so visitors never call their own localhost.
- `compose.hosted.yml` runs PostgreSQL privately and the application on port 8000, with separate persistent Docker volumes. These are new deployment records; local uploads/database files are not published.
- `.devcontainer/devcontainer.json` prepares this stack in a 2-core/8-GB GitHub Codespace. The Codespace starts the existing app automatically; the frontend, model, database and routes are genuine.
- `.github/workflows/container.yml` builds the deployment on GitHub's standard public-repository runner and tests the full synthetic upload-to-ranking workflow. It does not create paid infrastructure.

## Free-only condition

Codespaces is a cloud development/demo environment, **not permanent 24/7 website hosting**. GitHub personal accounts include a compute/storage allowance. Two-core compute consumes two core-hours per hour; storage also counts while a Codespace exists. Set a $0 Codespaces budget with usage stopping at the limit, check remaining allowance, and keep paid usage disabled before creating it. Idle stopping and short retention reduce consumption. No payment method or paid-plan upgrade is required for included-quota use.

Official references: [GitHub Codespaces billing](https://docs.github.com/en/billing/concepts/product-billing/github-codespaces), [Codespaces overview](https://docs.github.com/en/codespaces/about-codespaces/what-are-codespaces), [sharing forwarded ports](https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace).

## Launch

1. Confirm the $0 budget and unused allowance in your [GitHub billing settings](https://github.com/settings/billing).
2. Open [Create a Codespace](https://codespaces.new/Tejk20/AI-Resume-Checker) and select the two-core machine. The first build installs dependencies and downloads MPNet, so it can take several minutes.
3. Wait for the post-create/start check to print the app URL and successful API/frontend health checks.
4. In the Codespace **Ports** panel, open port **8000**. It is initially private to you. For a shareable demo, explicitly set that port's visibility to **Public**. The database port is not published.
5. Share the returned `https://<codespace-name>-8000.app.github.dev` URL. It works only while this Codespace and the application are running. It is not a GitHub Pages address.
6. Use synthetic documents from the repository for demonstration. Existing authentication/retention/production-hardening limitations still apply; do not upload real resumes to a public demo.

CLI alternative after granting the GitHub CLI `codespace` permission:

```powershell
gh auth refresh -h github.com -s codespace
gh codespace create -R Tejk20/AI-Resume-Checker -b main --idle-timeout 10m --retention-period 24h --display-name resume-checker-demo
# Use the actual returned Codespace name:
gh codespace ports visibility 8000:public -c <codespace-name>
```

No Codespace is automatically created by the repository's workflow. Creating one requires the account's authorization and available free allowance. Stop it from the Codespaces page when finished and delete it when no longer needed to release storage.

## Other container hosts

The same Docker image can run on another provider with at least 2 GB RAM and PostgreSQL, without modifying the application. Set `DATABASE_URL` (plain `postgres://`/`postgresql://` URLs are accepted), `PORT`, and optional model/cache/batch settings. Set a persistent upload directory/volume if original files must survive restarts. A host account and enough memory are required; do not select a paid plan without approval.
