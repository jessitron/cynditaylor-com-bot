from bedrock_agentcore import BedrockAgentCoreApp

from agent.cyndibot import build_agent
from agent.observability import configure_tracing

app = BedrockAgentCoreApp()

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        configure_tracing()
        _agent = build_agent()
    return _agent


@app.entrypoint
def invoke(payload):
    s3_key = payload["s3_key"]
    agent = _get_agent()
    result = agent(f"The inbound email is at S3 key: {s3_key}")
    return {"result": str(result.message)}


if __name__ == "__main__":
    app.run()
