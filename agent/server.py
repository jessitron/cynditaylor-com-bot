from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext
from opentelemetry import trace

from agent.cyndibot import build_agent
from agent.observability import configure_tracing

app = BedrockAgentCoreApp()

_agent = None


def _get_agent(session_id: str | None, email_from: str | None):
    global _agent
    if _agent is None:
        configure_tracing(session_id=session_id, email_from=email_from)
        _agent = build_agent()
    return _agent


@app.entrypoint
def invoke(payload, context: RequestContext):
    s3_key = payload["s3_key"]
    email_thread_id = payload.get("email_thread_id", "")
    invocation_id = payload.get("invocation_id", "")
    email_from = payload.get("email_from", "")
    agent = _get_agent(context.session_id, email_from)
    tracer = trace.get_tracer("agent.server")
    with tracer.start_as_current_span("agent.invocation") as span:
        if email_thread_id:
            span.set_attribute("email.thread.id", email_thread_id)
        if invocation_id:
            span.set_attribute("invocation.id", invocation_id)
        if email_from:
            span.set_attribute("email.from", email_from)
        result = agent(f"The inbound email is at S3 key: {s3_key}")
    return {"result": str(result.message)}


if __name__ == "__main__":
    app.run()
