#!/usr/bin/env bash
set -euo pipefail

cd /app

# Configure non-interactive git credential helper from GITHUB_PAT when provided.
# Credentials are read from the process environment at runtime and never written into repository files.
if [[ -n "${GITHUB_PAT:-}" ]]; then
  git config --global credential.helper '!f() { echo "username=x-access-token"; echo "password=${GITHUB_PAT}"; }; f'
fi

git config --global advice.detachedHead false

# Optional startup sync against origin/staging/provider-shared so scale-from-zero containers
# always start at the latest remote shared staging commit before serving MCP requests.
if [[ "${GENESIS_SYNC_ON_START:-0}" == "1" ]]; then
  BRANCH="${GENESIS_GIT_BRANCH:-staging/provider-shared}"
  git fetch --quiet origin "${BRANCH}"
  git checkout --quiet -B "${BRANCH}" "origin/${BRANCH}"
fi

ARGS=(
  "serve"
  "--host" "${HOST:-0.0.0.0}"
  "--port" "${PORT:-8080}"
)

if [[ -n "${GENESIS_SHARED_SCOPE:-}" ]]; then
  ARGS+=("--shared" "${GENESIS_SHARED_SCOPE}")
else
  ARGS+=("--campaign" "${GENESIS_CAMPAIGN_DIR}" "--id" "${GENESIS_CAMPAIGN_ID}" "--store" "${GENESIS_STORE_PATH}")
fi

if [[ "${GENESIS_MCP_READ_ONLY:-1}" == "1" || "${GENESIS_MCP_READ_ONLY:-}" == "true" ]]; then
  ARGS+=("--read-only")
fi

exec python3 -B /app/development/gm_provider/service.py "${ARGS[@]}"
