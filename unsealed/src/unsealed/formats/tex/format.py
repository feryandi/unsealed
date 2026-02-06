import re

from pathlib import Path
from typing import Type, Pattern

from ...assets.blob import Blob
from ..base import BaseFormat
from ..tex.decoder import SealTextureDecoder


class SealTextureFormat(BaseFormat[Blob]):
  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.(tex|te1)$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Blob]:
    return Blob

  def decoder(self, path: Path) -> Blob:
    decoder = SealTextureDecoder(path)
    texture = decoder.decode()
    texture.filename = path.stem
    return texture

  def encoder(self, asset: Blob, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
