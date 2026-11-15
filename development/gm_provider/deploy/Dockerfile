FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends git nodejs ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 genesis && useradd --uid 10001 --gid 10001 --create-home genesis
WORKDIR /app
COPY development/gm_provider/requirements-mcp.txt /app/requirements-mcp.txt
RUN pip install --no-cache-dir -r requirements-mcp.txt PyYAML==6.0.3
COPY . /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/home/genesis
EXPOSE 10000
CMD ["python3", "-B", "development/gm_provider/deploy/start.py"]
