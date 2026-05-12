"""
Pipeline for .tex / .te1 texture files — produces an ImageScene.
Also provides low-level texture decoding reusable by other pipelines.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional, Tuple

from ..scenes import ImageScene, MapScene, ModelScene


class TexViewerPipeline:
  """Decode a .tex / .te1 (or plain image) texture file into an ImageScene."""

  def run(self, path: Path) -> ImageScene:
    image, w, h = TexViewerPipeline.decode(path)
    return ImageScene(image=image, image_w=w, image_h=h)

  @staticmethod
  def decode(path: Path) -> Tuple[Optional[bytes], int, int]:
    """Decode any supported texture file → (rgba_bytes, w, h).

    Reusable entry point for other pipelines that need raw texture pixel data.
    """
    if path.suffix.lower() in (".tex", ".te1"):
      return TexViewerPipeline._decode_seal_texture(path)
    return TexViewerPipeline._decode_image_file(path)

  @staticmethod
  def _decode_seal_texture(path: Path) -> Tuple[Optional[bytes], int, int]:
    """Decode a .tex / .te1 file via SealTextureDecoder → raw RGBA bytes."""
    try:
      from ...formats.tex.decoder import SealTextureDecoder

      blob = SealTextureDecoder(path).decode()
      if blob.value:
        return TexViewerPipeline._pil_bytes_from_raw(blob.value)
    except Exception:
      pass
    return None, 0, 0

  @staticmethod
  def _decode_image_file(path: Path) -> Tuple[Optional[bytes], int, int]:
    """Decode a plain image file (PNG, JPG, BMP…) via PIL → raw RGBA bytes."""
    try:
      from PIL import Image

      img = Image.open(path).convert("RGBA")
      return img.tobytes(), img.width, img.height
    except Exception:
      return None, 0, 0

  @staticmethod
  def _pil_bytes_from_raw(data: bytes) -> Tuple[Optional[bytes], int, int]:
    """Decode arbitrary image bytes (DDS, JPG, BMP…) via PIL → raw RGBA bytes."""
    try:
      from PIL import Image

      img = Image.open(io.BytesIO(data)).convert("RGBA")
      return img.tobytes(), img.width, img.height
    except Exception:
      return None, 0, 0
