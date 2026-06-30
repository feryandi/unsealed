"""
Pipeline for .tex / .te1 texture files — produces an ImageScene.
Also provides low-level texture decoding reusable by other pipelines.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional, Tuple, Union

from ....vfs import Resource
from .scene import ImageScene


class TexViewerPipeline:
  """Decode a .tex / .te1 (or plain image) texture file into an ImageScene."""

  def run(self, res: Resource) -> ImageScene:
    image, w, h = TexViewerPipeline.decode(res)
    return ImageScene(image=image, image_w=w, image_h=h)

  @staticmethod
  def decode(target: Union[Path, Resource]) -> Tuple[Optional[bytes], int, int]:
    """Decode any supported texture file → (rgba_bytes, w, h).

    Reusable entry point for other pipelines needing raw texture pixels;
    accepts a vfs Resource or a plain disk Path.
    """
    res = target if isinstance(target, Resource) else Resource.for_disk_file(target)
    if res.suffix.lower() in (".tex", ".te1"):
      return TexViewerPipeline._decode_seal_texture(res)
    return TexViewerPipeline._decode_image_file(res)

  @staticmethod
  def _decode_seal_texture(res: Resource) -> Tuple[Optional[bytes], int, int]:
    """Decode a .tex / .te1 via SealTextureDecoder → raw RGBA bytes."""
    try:
      from unsealed.formats.tex.decoder import SealTextureDecoder

      blob = SealTextureDecoder(res).decode()
      if blob.value:
        return TexViewerPipeline._pil_bytes_from_raw(blob.value)
    except Exception:
      pass
    return None, 0, 0

  @staticmethod
  def _decode_image_file(res: Resource) -> Tuple[Optional[bytes], int, int]:
    """Decode a plain image file (PNG, JPG, BMP…) via PIL → raw RGBA bytes."""
    try:
      from PIL import Image

      img = Image.open(io.BytesIO(res.read())).convert("RGBA")
      return img.tobytes(), img.width, img.height
    except Exception:
      return None, 0, 0

  @staticmethod
  def _pil_bytes_from_raw(data: bytes) -> Tuple[Optional[bytes], int, int]:
    """Decode arbitrary image bytes (DDS, JPG, BMP…) via PIL → raw RGBA."""
    try:
      from PIL import Image

      img = Image.open(io.BytesIO(data)).convert("RGBA")
      return img.tobytes(), img.width, img.height
    except Exception:
      return None, 0, 0
