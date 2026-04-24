FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY agent ./agent

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV CYNDIBOT_WORKSPACE=/mnt/workspace/cynditaylor-com
ENV OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://host.docker.internal:6006/v1/traces

EXPOSE 8080

CMD ["python", "-m", "agent.server"]
