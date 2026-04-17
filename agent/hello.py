import boto3
from opentelemetry import trace

from agent.observability import configure_tracing

REGION = "us-west-2"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


def main() -> None:
    tracer = configure_tracing()
    client = boto3.client("bedrock-runtime", region_name=REGION)

    with tracer.start_as_current_span("bedrock.converse") as span:
        span.set_attribute("bedrock.model_id", MODEL_ID)
        span.set_attribute("bedrock.region", REGION)

        response = client.converse(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "Say hello to Cyndi in one short sentence."}],
                }
            ],
            inferenceConfig={"maxTokens": 200, "temperature": 0.7},
        )

        usage = response.get("usage", {})
        span.set_attribute("bedrock.input_tokens", usage.get("inputTokens", 0))
        span.set_attribute("bedrock.output_tokens", usage.get("outputTokens", 0))

        for block in response["output"]["message"]["content"]:
            if "text" in block:
                print(block["text"])

    trace.get_tracer_provider().shutdown()


if __name__ == "__main__":
    main()
