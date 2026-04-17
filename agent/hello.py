from opentelemetry import trace
from strands import Agent
from strands.models import BedrockModel

from agent.observability import configure_tracing

REGION = "us-west-2"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


def main() -> None:
    configure_tracing()

    model = BedrockModel(model_id=MODEL_ID, region_name=REGION)
    agent = Agent(
        model=model,
        system_prompt="You are a friendly assistant. Keep replies short.",
    )

    agent("Say hello to Cyndi in one short sentence.")
    print()

    trace.get_tracer_provider().shutdown()


if __name__ == "__main__":
    main()
