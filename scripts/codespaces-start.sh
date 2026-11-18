#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${1:-}" == "--build" ]]; then
  docker compose -f compose.hosted.yml build
fi
docker compose -f compose.hosted.yml up -d --wait --wait-timeout 180
docker compose -f compose.hosted.yml exec -T app python scripts/check_hosted_http.py
if [[ -n "${CODESPACE_NAME:-}" ]]; then
  echo "App URL: https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  echo "The port is private until you explicitly set its visibility to public."
else
  echo "App URL: http://localhost:8000"
fi
