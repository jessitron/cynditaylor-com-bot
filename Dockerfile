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
ENV OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental
# Strands' tracer puts gen_ai.{input,output}.messages on span events, and only
# also copies them onto span attributes when it detects Langfuse via a
# substring match in this var. Honeycomb queries attrs, not events, so we
# trip the heuristic. See strands/telemetry/tracer.py is_langfuse / _add_event.
# The substring "langfuse" is what trips Strands' is_langfuse heuristic.
ENV LANGFUSE_BASE_URL=langfuse-stub-for-honeycomb

EXPOSE 8080

CMD ["python", "-m", "agent.server"]
