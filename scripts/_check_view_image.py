"""Smoke-test view_site_image_impl end-to-end:
1. wrap an existing site image into a Strands ToolResult
2. send the image to Bedrock (Claude Sonnet 4.5) and print its description
   -- proving the model actually sees what view_site_image returned.
"""

import sys

import boto3

from agent.tools.site_tools import WORKSPACE_DIR, view_site_image_impl

REGION = "us-west-2"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
TARGET = "images/breakfast-for-one.jpg"


def main() -> int:
    target_path = WORKSPACE_DIR / TARGET
    if not target_path.is_file():
        print(f"FAIL: {target_path} not in workspace -- run sync_workspace first")
        return 1

    print(f"viewing: {TARGET}  (on disk: {target_path.stat().st_size} bytes)")
    result = view_site_image_impl(TARGET)
    assert result["status"] == "success", result
    image_blocks = [c for c in result["content"] if "image" in c]
    assert len(image_blocks) == 1, result
    image_content = image_blocks[0]
    raw = image_content["image"]["source"]["bytes"]
    print(f"wrapped: format={image_content['image']['format']} bytes={len(raw)}")

    print("asking Bedrock to describe it...")
    bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    resp = bedrock.converse(
        modelId=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [
                    image_content,
                    {
                        "text": (
                            "This is a painting from a website's gallery. "
                            "Describe what you see in 2-3 sentences -- subject, "
                            "colors, mood. This is a smoke test for an image "
                            "tool; if you can see the image, your description "
                            "proves it works."
                        )
                    },
                ],
            }
        ],
    )

    text_parts = [
        c["text"] for c in resp["output"]["message"]["content"] if "text" in c
    ]
    description = "\n".join(text_parts).strip()
    print()
    print("=== model description ===")
    print(description)
    print("=========================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
