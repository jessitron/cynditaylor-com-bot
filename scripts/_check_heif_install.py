"""Quick verification that pillow + pillow-heif loaded correctly and can
register the HEIF opener. Run after changing deps or container base
image. Does not touch any files; just exercises the import + register
path."""

import pillow_heif
from PIL import Image

pillow_heif.register_heif_opener()
print(f"pillow-heif: {pillow_heif.__version__}")
print(f"PIL: {Image.__version__}")
print("HEIF opener registered.")
