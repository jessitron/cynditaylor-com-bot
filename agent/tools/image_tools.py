"""Leaf tools for image transformation. Used by the image subagent."""

from typing import Any

from opentelemetry import trace
from PIL import Image, ImageOps
from strands import tool

from agent.tools.site_tools import WORKSPACE_DIR, _validate_path

_tracer = trace.get_tracer(__name__)

_PIL_FORMATS = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "gif": "GIF",
    "webp": "WEBP",
}

# PIL's ROTATE_N is counter-clockwise N degrees. Map clockwise -> PIL transpose.
_CW_TO_TRANSPOSE = {
    90: Image.ROTATE_270,
    180: Image.ROTATE_180,
    270: Image.ROTATE_90,
}


def _format_for(path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix not in _PIL_FORMATS:
        raise ValueError(
            f"unsupported image format {path.suffix!r}; "
            f"supported: {sorted(set(_PIL_FORMATS.keys()))}"
        )
    return _PIL_FORMATS[suffix]


def _save(img: Image.Image, target_path, fmt: str) -> None:
    save_kwargs: dict[str, Any] = {"format": fmt}
    if fmt == "JPEG":
        save_kwargs["quality"] = 90
        if img.mode != "RGB":
            img = img.convert("RGB")
    img.save(target_path, **save_kwargs)


def resize_site_image_impl(path: str, max_edge: int) -> dict[str, Any]:
    target = _validate_path(path)
    if not target.is_file():
        raise FileNotFoundError(f"no such file in workspace: {path!r}")
    if max_edge < 16 or max_edge > 8192:
        raise ValueError(f"max_edge must be between 16 and 8192, got {max_edge}")
    fmt = _format_for(target)

    with _tracer.start_as_current_span("resize_site_image") as span:
        rel = str(target.relative_to(WORKSPACE_DIR))
        span.set_attribute("image.path", rel)
        span.set_attribute("image.max_edge", max_edge)
        img = ImageOps.exif_transpose(Image.open(target))
        span.set_attribute("image.input_width", img.width)
        span.set_attribute("image.input_height", img.height)
        long_edge = max(img.width, img.height)

        if long_edge <= max_edge:
            span.set_attribute("image.changed", False)
            return {
                "path": rel,
                "width": img.width,
                "height": img.height,
                "changed": False,
                "reason": f"long edge already <= {max_edge}px",
            }

        scale = max_edge / long_edge
        new_size = (int(img.width * scale), int(img.height * scale))
        resized = img.resize(new_size, Image.LANCZOS)
        _save(resized, target, fmt)
        out_bytes = target.stat().st_size
        span.set_attribute("image.output_width", new_size[0])
        span.set_attribute("image.output_height", new_size[1])
        span.set_attribute("image.output_bytes", out_bytes)
        span.set_attribute("image.changed", True)
        return {
            "path": rel,
            "width": new_size[0],
            "height": new_size[1],
            "bytes": out_bytes,
            "changed": True,
        }


def rotate_site_image_impl(path: str, degrees: int) -> dict[str, Any]:
    target = _validate_path(path)
    if not target.is_file():
        raise FileNotFoundError(f"no such file in workspace: {path!r}")
    if degrees not in _CW_TO_TRANSPOSE:
        raise ValueError(
            f"degrees must be one of 90, 180, 270 (clockwise), got {degrees!r}"
        )
    fmt = _format_for(target)

    with _tracer.start_as_current_span("rotate_site_image") as span:
        rel = str(target.relative_to(WORKSPACE_DIR))
        span.set_attribute("image.path", rel)
        span.set_attribute("image.rotate_degrees_clockwise", degrees)
        img = ImageOps.exif_transpose(Image.open(target))
        span.set_attribute("image.input_width", img.width)
        span.set_attribute("image.input_height", img.height)
        rotated = img.transpose(_CW_TO_TRANSPOSE[degrees])
        _save(rotated, target, fmt)
        out_bytes = target.stat().st_size
        span.set_attribute("image.output_width", rotated.width)
        span.set_attribute("image.output_height", rotated.height)
        span.set_attribute("image.output_bytes", out_bytes)
        return {
            "path": rel,
            "width": rotated.width,
            "height": rotated.height,
            "bytes": out_bytes,
            "rotated_degrees_clockwise": degrees,
        }


@tool
def resize_site_image(path: str, max_edge: int) -> dict[str, Any]:
    """Resize an image in the site workspace, preserving aspect ratio, in place.

    EXIF orientation is normalized first, so the result has correct
    pixel orientation regardless of how the camera tagged the file.
    If the image's long edge is already <= max_edge, returns
    changed=False without rewriting the file.

    Args:
        path: Path relative to the workspace root, e.g. "images/garden.jpg".
        max_edge: Target maximum length (pixels) for the long edge.
            Typical values: 1600 for full-width photos, 800 for thumbnails.
    """
    return resize_site_image_impl(path, max_edge)


@tool
def rotate_site_image(path: str, degrees: int) -> dict[str, Any]:
    """Rotate an image clockwise by 90, 180, or 270 degrees, in place.

    EXIF orientation is normalized first, so the rotation is applied
    relative to how the image actually displays in a browser.

    Args:
        path: Path relative to the workspace root, e.g. "images/garden.jpg".
        degrees: 90, 180, or 270 (clockwise). Other values are rejected.
    """
    return rotate_site_image_impl(path, degrees)
