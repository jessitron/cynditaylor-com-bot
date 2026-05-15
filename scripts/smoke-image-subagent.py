#!/usr/bin/env -S uv run --quiet python
"""Smoke test: image tools and subagent wire up cleanly.

Builds the parent agent (no model call), exercises resize_site_image
and rotate_site_image directly against a temp workspace, and confirms
edit_images is in the parent's tool list.
"""

import os
import tempfile
from pathlib import Path

# Point the workspace at a temp dir BEFORE importing anything that
# resolves WORKSPACE_DIR at import time.
_tmp = tempfile.mkdtemp(prefix="cyndibot-smoke-")
os.environ["CYNDIBOT_WORKSPACE"] = _tmp

from PIL import Image  # noqa: E402

from agent.cyndibot import build_agent  # noqa: E402
from agent.image_subagent import build_image_agent, edit_images  # noqa: E402
from agent.tools.image_tools import (  # noqa: E402
    image_info_impl,
    resize_site_image_impl,
    rotate_site_image_impl,
)
from agent.tools.site_tools import view_site_image_impl  # noqa: E402


def main() -> None:
    workspace = Path(_tmp)
    images = workspace / "images"
    images.mkdir(parents=True)

    portrait = Image.new("RGB", (4000, 3000), color=(120, 80, 40))
    portrait.save(images / "garden.jpg", quality=90)

    print(f"workspace: {workspace}")
    print(f"input:     {(images / 'garden.jpg').stat().st_size} bytes, 4000x3000")

    info = image_info_impl("images/garden.jpg")
    print(f"info:      {info}")
    assert info["width"] == 4000
    assert info["height"] == 3000
    assert info["format"] == "jpeg"
    assert info["bytes"] > 0

    view = view_site_image_impl("images/garden.jpg")
    view_text = view["content"][0]["text"]
    print(f"view text: {view_text}")
    assert "4000x3000" in view_text, view_text

    rotate_result = rotate_site_image_impl("images/garden.jpg", 90)
    print(f"rotate:    {rotate_result}")
    assert rotate_result["width"] == 3000
    assert rotate_result["height"] == 4000

    info_after_rotate = image_info_impl("images/garden.jpg")
    assert info_after_rotate["width"] == 3000
    assert info_after_rotate["height"] == 4000

    resize_result = resize_site_image_impl("images/garden.jpg", 1600)
    print(f"resize:    {resize_result}")
    assert resize_result["changed"] is True
    assert max(resize_result["width"], resize_result["height"]) == 1600

    skip_result = resize_site_image_impl("images/garden.jpg", 1600)
    print(f"reresize:  {skip_result}")
    assert skip_result["changed"] is False

    image_agent = build_image_agent()
    sub_tool_names = [t.tool_name for t in image_agent.tool_registry.registry.values()]
    print(f"subagent tools: {sub_tool_names}")
    assert "image_info" in sub_tool_names, sub_tool_names

    parent = build_agent(thread_id="smoke")
    parent_tool_names = [t.tool_name for t in parent.tool_registry.registry.values()]
    print(f"parent tools:   {parent_tool_names}")
    assert "edit_images" in parent_tool_names, parent_tool_names
    assert "image_info" in parent_tool_names, parent_tool_names

    assert callable(edit_images)
    print("OK")


if __name__ == "__main__":
    main()
