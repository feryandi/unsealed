"""`.tex` / `.te1` textures -> an image preview beside its properties.

The decoder yields opaque image bytes (or pre-decoded RGBA), so we
render the picture on the left and list file/image properties (type,
dimensions, byte counts) on the right, Windows-style.
"""

from io import BytesIO
from typing import Optional

from PIL import Image
from PySide6.QtGui import QPixmap

from ....assets.blob import Blob
from ....formats.tex.format import SealTextureFormat
from ....vfs import Resource
from ..image_view import ImageView, file_meta, pil_to_pixmap, size_row
from ..registry import ContentContext, FormatHandler, register

_TYPE_NAMES = {".tex": "TEX texture", ".te1": "TE1 texture"}


def _decode(resource: Resource) -> Blob:
  return SealTextureFormat().decode(resource)


def _image_info(blob: Blob) -> tuple[int, int, str] | None:
  """Width, height and colour mode of the decoded image, if readable."""
  if blob.value:
    try:
      with Image.open(BytesIO(blob.value)) as im:
        return im.width, im.height, im.mode
    except Exception:
      return None
  if blob.image_rgba is not None:
    return blob.width, blob.height, "RGBA"
  return None


def _pixmap(blob: Blob) -> Optional[QPixmap]:
  """Render the Blob to a QPixmap from encoded bytes or raw RGBA."""
  try:
    if blob.value:
      with Image.open(BytesIO(blob.value)) as im:
        im.load()
        return pil_to_pixmap(im)
    if blob.image_rgba is not None and blob.width and blob.height:
      im = Image.frombytes("RGBA", (blob.width, blob.height), blob.image_rgba)
      return pil_to_pixmap(im)
  except Exception:
    return None
  return None


def _view(blob: Blob, ctx: ContentContext) -> ImageView:
  resource = ctx.resource
  suffix = resource.suffix.lower()
  location, byte_size = file_meta(resource)
  file_rows = [
    ("Name", resource.name),
    ("Type", _TYPE_NAMES.get(suffix, "Texture")),
    ("Location", location),
    ("Size", size_row(byte_size)),
  ]

  image_rows = [("Image format", (blob.extension or "unknown").upper())]
  info = _image_info(blob)
  if info is not None:
    width, height, mode = info
    image_rows += [
      ("Dimensions", f"{width} × {height} px"),
      ("Width", f"{width} pixels"),
      ("Height", f"{height} pixels"),
      ("Color mode", mode),
    ]
  else:
    image_rows.append(("Dimensions", "unknown"))
  if blob.value is not None:
    image_rows.append(("Decoded size", size_row(len(blob.value))))

  return ImageView(_pixmap(blob), [("File", file_rows), ("Image", image_rows)])


register(
  FormatHandler(
    name="Texture",
    extensions=(".tex", ".te1"),
    decode=_decode,
    view=_view,
  )
)
