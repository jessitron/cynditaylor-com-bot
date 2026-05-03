from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext
from opentelemetry import trace

from agent.cyndibot import build_agent
from agent.observability import configure_tracing

app = BedrockAgentCoreApp()

_agent = None


def _get_agent(session_id: str | None):
    global _agent
    if _agent is None:
        configure_tracing(session_id=session_id)
        _agent = build_agent()
    return _agent


@app.entrypoint
def invoke(payload, context: RequestContext):
    s3_key = payload["s3_key"]
    agent = _get_agent(context.session_id)
    tracer = trace.get_tracer("agent.server")
    with tracer.start_as_current_span("agent.invocation"):
        result = agent(f"The inbound email is at S3 key: {s3_key}")
    return {"result": str(result.message)}


if __name__ == "__main__":
    app.run()
