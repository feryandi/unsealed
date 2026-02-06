import re
from PIL import Image

from pathlib import Path
from typing import Pattern, Type
import numpy as np

from ..base import BaseFormat
from ...assets.terrain import Terrain


class HeightmapFormat(BaseFormat[Terrain]):
  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.png$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Terrain]:
    return Terrain

  def decoder(self, path: Path) -> Terrain:
    raise NotImplementedError("Decoder is not implemented")

  def encoder(self, asset: Terrain, path: Path) -> None:
    heightmap = np.array(asset.heightmap)
    altitudes = heightmap.reshape(asset.height, asset.width)

    alt_min = altitudes.min()
    alt_range = altitudes.max() - alt_min

    if alt_range > 0:
      altitudes -= alt_min
      altitudes *= 65535.0 / alt_range

    # Convert to uint16
    altitudes = altitudes.astype(np.uint16)

    # Mode 'I;16' is for 16-bit unsigned integer grayscale
    img = Image.fromarray(altitudes, mode="I;16")
    img.save(path)
