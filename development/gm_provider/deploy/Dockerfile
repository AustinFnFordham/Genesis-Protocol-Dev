# Syntax: docker/dockerfile:1
# Minimal container for the Genesis Protocol HTTP + Remote MCP Gateway (`service.py` + `mcp_adapter.py`).
# Includes Python 3.11, PyYAML, Node.js (for `turn_contract.js` validation/linting), and Git (for `GitStore`).

FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "PyYAML>=6.0.1"

WORKDIR /app
COPY . /app

RUN chmod +x /app/development/gm_provider/deploy/entrypoint.sh \
    && useradd --create-home --shell /bin/bash genesis \
    && chown -R genesis:genesis /app

USER genesis

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080 \
    GENESIS_SHARED_SCOPE=staging/shared-1 \
    GENESIS_MCP_READ_ONLY=1

EXPOSE 8080

ENTRYPOINT ["/app/development/gm_provider/deploy/entrypoint.sh"]
