import re

from pathlib import Path
from typing import Pattern, Type


from ..base import BaseFormat
from ...assets.shader import Shaders
from ..sha.decoder import SealShaDecoder


class SealShaFormat(BaseFormat[Shaders]):
  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.sha$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Shaders]:
    return Shaders

  def decoder(self, path: Path) -> Shaders:
    decoder = SealShaDecoder(path)
    shaders = decoder.decode()
    return shaders

  def encoder(self, asset: Shaders, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
