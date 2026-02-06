import re

from pathlib import Path
from typing import Pattern, Type

from ..base import BaseFormat
from ...assets.terrain import Terrain
from ..map.decoder import SealMapDecoder


class SealMapFormat(BaseFormat[Terrain]):
  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.map$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Terrain]:
    return Terrain

  def decoder(self, path: Path) -> Terrain:
    map_decoder = SealMapDecoder(path)
    terrain = map_decoder.decode()
    return terrain

  def encoder(self, asset: Terrain, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
