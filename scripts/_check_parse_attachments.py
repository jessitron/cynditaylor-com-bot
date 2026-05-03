"""Run parse_inbound_impl on a staged S3 key and verify attachment
extraction + HEIC conversion. Exits non-zero on any check failure.

Used by scripts/smoke-parse-attachments. NOT a unit test framework
because the project policy is no tests unless asked; this is a smoke
check that exercises real S3 + filesystem."""

import json
import sys
from pathlib import Path

from agent.tools.email_tools import parse_inbound_impl
from agent.tools.site_tools import WORKSPACE_DIR


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: _check_parse_attachments.py <s3_key>")
    s3_key = sys.argv[1]

    result = parse_inbound_impl(s3_key)
    print(json.dumps(result, indent=2, default=str))
    print()

    attachments = result["attachments"]
    if len(attachments) != 2:
        raise SystemExit(f"expected 2 attachments, got {len(attachments)}")

    by_orig = {a["original_filename"]: a for a in attachments}

    heic = by_orig.get("smoke-red.heic")
    if heic is None:
        raise SystemExit(f"no HEIC attachment found in: {list(by_orig)}")
    if heic["content_type"] != "image/jpeg":
        raise SystemExit(
            f"expected HEIC->JPG content_type=image/jpeg, got {heic['content_type']}"
        )
    if not heic["path"].endswith(".jpg"):
        raise SystemExit(f"expected .jpg path for HEIC, got {heic['path']}")

    jpg = by_orig.get("smoke-blue.jpg")
    if jpg is None:
        raise SystemExit(f"no JPEG attachment found in: {list(by_orig)}")
    if jpg["content_type"] != "image/jpeg":
        raise SystemExit(
            f"expected JPEG content_type=image/jpeg, got {jpg['content_type']}"
        )

    for a in attachments:
        on_disk = WORKSPACE_DIR / a["path"]
        if not on_disk.exists():
            raise SystemExit(f"attachment not on disk: {on_disk}")
        actual = on_disk.stat().st_size
        if actual != a["size_bytes"]:
            raise SystemExit(
                f"size mismatch for {a['path']}: meta={a['size_bytes']}, disk={actual}"
            )

    print("=== PASS ===")
    print(f"  HEIC -> JPG: {heic['path']} ({heic['size_bytes']} bytes)")
    print(f"  JPEG:        {jpg['path']} ({jpg['size_bytes']} bytes)")

    print()
    print("Cleaning up the just-written files (next sync_workspace would clean them too):")
    for a in attachments:
        p = WORKSPACE_DIR / a["path"]
        p.unlink()
        print(f"  rm {p}")


if __name__ == "__main__":
    main()
