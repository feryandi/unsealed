"""Standard images (`.png`/`.jpg`/`.dds`/…) -> preview + properties.

These aren't a game format — they're ordinary image files (often the
raw art a `.tex` was packed from, or something a user drops in). We read
the bytes, decode with PIL, and show the same preview-beside-properties
layout the texture handler uses.
"""

from io import BytesIO
from typing import Optional

from PIL import Image
from PySide6.QtGui import QPixmap

from ....vfs import Resource
from ..image_view import ImageView, file_meta, pil_to_pixmap, size_row
from ..registry import ContentContext, FormatHandler, register

_TYPE_NAMES = {
  ".png": "PNG image",
  ".jpg": "JPEG image",
  ".jpeg": "JPEG image",
  ".dds": "DDS texture",
  ".bmp": "Bitmap image",
  ".gif": "GIF image",
  ".tga": "Targa image",
  ".webp": "WebP image",
}


def _decode(resource: Resource) -> bytes:
  # Nothing to decode: hand the raw bytes to the view, which lets PIL
  # decode both the preview and the reported dimensions from one source.
  return resource.read()


def _open(data: bytes) -> Optional[Image.Image]:
  try:
    image = Image.open(BytesIO(data))
    image.load()
    return image
  except Exception:
    return None


def _view(data: bytes, ctx: ContentContext) -> ImageView:
  resource = ctx.resource
  suffix = resource.suffix.lower()
  location, byte_size = file_meta(resource)
  file_rows = [
    ("Name", resource.name),
    ("Type", _TYPE_NAMES.get(suffix, "Image")),
    ("Location", location),
    ("Size", size_row(byte_size)),
  ]

  image = _open(data)
  pixmap: Optional[QPixmap] = pil_to_pixmap(image) if image is not None else None
  if image is not None:
    image_rows = [
      ("Image format", (image.format or suffix.lstrip(".")).upper()),
      ("Dimensions", f"{image.width} × {image.height} px"),
      ("Width", f"{image.width} pixels"),
      ("Height", f"{image.height} pixels"),
      ("Color mode", image.mode),
    ]
  else:
    image_rows = [("Dimensions", "unreadable")]

  return ImageView(pixmap, [("File", file_rows), ("Image", image_rows)])


register(
  FormatHandler(
    name="Image",
    extensions=tuple(_TYPE_NAMES.keys()),
    decode=_decode,
    view=_view,
  )
)
