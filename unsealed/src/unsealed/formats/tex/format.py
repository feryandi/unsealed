import re

from pathlib import Path
from typing import Type, Pattern

from ...assets.blob import Blob
from ...vfs import Resource
from ..base import BaseFormat
from ..tex.decoder import SealTextureDecoder


class SealTextureFormat(BaseFormat[Blob]):
  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.(tex|te1)$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Blob]:
    return Blob

  def decoder(self, res: Resource) -> Blob:
    decoder = SealTextureDecoder(res.open())
    texture = decoder.decode()
    texture.name = res.stem
    return texture

  def encoder(self, asset: Blob, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
