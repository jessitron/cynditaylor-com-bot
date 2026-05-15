"""Image-editing subagent. Exposed to the parent via the edit_images tool."""

from strands import Agent, tool
from strands.models import BedrockModel

from agent.tools.image_tools import resize_site_image, rotate_site_image
from agent.tools.site_tools import view_site_image

REGION = "us-west-2"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are Cyndibot's image-editing subagent.

You receive a plain-English instruction about one or more images that
are already on disk in the site workspace (paths relative to the
workspace root, e.g. "images/garden.jpg"). Your job:

  1. Use view_site_image to look at each image first, so you know its
     current orientation and dimensions.
  2. Apply rotate_site_image and/or resize_site_image as needed.
     - Rotation is 90, 180, or 270 degrees clockwise only.
     - Resize is by max_edge (long edge in pixels). For web display
       on Cyndi's site, 1600px is a sensible default unless the
       parent asks for something specific.
  3. If you're unsure the result is correct (e.g. you rotated and want
     to confirm orientation), use view_site_image again to verify.
  4. Return a short summary listing each image you touched and its
     final dimensions. If you decided no edit was needed, say so and
     why.

You do NOT commit, push, or edit HTML. You only transform image
files. The parent agent handles git and HTML.
"""


def build_image_agent() -> Agent:
    model = BedrockModel(model_id=MODEL_ID, region_name=REGION)
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[view_site_image, resize_site_image, rotate_site_image],
    )


@tool
def edit_images(instructions: str) -> str:
    """Delegate image transformation to the image-editing subagent.

    Use this when Cyndi asks for an image to be rotated or resized, or
    when you notice an attachment is sideways or much larger than
    needed for the web (typical phone photo is ~4000px; the site wants
    ~1600px max). Do NOT use this for deciding where the image goes on
    the page -- that's your job, not the subagent's.

    Examples of good instructions:
      - "Rotate images/garden.jpg 90 degrees clockwise -- it's sideways."
      - "Resize images/portrait.jpg so the long edge is 1600px."
      - "images/sunset.jpg is sideways and huge -- rotate it upright
         and resize to 1600px max edge."

    Args:
        instructions: Plain-English directive. Name the file paths
            (relative to workspace root) and what to do.

    Returns:
        Short text summary of what the subagent did, including final
        dimensions.
    """
    agent = build_image_agent()
    return str(agent(instructions))
