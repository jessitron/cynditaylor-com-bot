import boto3

REGION = "us-west-2"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


def main() -> None:
    client = boto3.client("bedrock-runtime", region_name=REGION)
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
    for block in response["output"]["message"]["content"]:
        if "text" in block:
            print(block["text"])


if __name__ == "__main__":
    main()
