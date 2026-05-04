"""Smoke-test view_site_image_impl on an existing image in the workspace."""

import sys
from pathlib import Path

from agent.tools.site_tools import WORKSPACE_DIR, view_site_image_impl


def main() -> int:
    images_dir = WORKSPACE_DIR / "images"
    if not images_dir.is_dir():
        print(f"FAIL: no images/ dir at {images_dir}")
        return 1

    candidates = [
        p for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ]
    if not candidates:
        print(f"FAIL: no supported images under {images_dir}")
        return 1

    target = max(candidates, key=lambda p: p.stat().st_size)
    rel = target.relative_to(WORKSPACE_DIR)
    print(f"viewing: {rel}  (on disk: {target.stat().st_size} bytes)")

    result = view_site_image_impl(str(rel))
    assert result["status"] == "success", result
    content = result["content"]
    assert any("text" in c for c in content), content
    image_blocks = [c for c in content if "image" in c]
    assert len(image_blocks) == 1, content
    img = image_blocks[0]["image"]
    assert img["format"] in {"jpeg", "png", "gif", "webp"}, img
    raw = img["source"]["bytes"]
    assert isinstance(raw, bytes) and len(raw) > 0, type(raw)
    print(f"ok: format={img['format']} returned_bytes={len(raw)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
