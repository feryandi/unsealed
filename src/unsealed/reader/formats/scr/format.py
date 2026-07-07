import re
from pathlib import Path
from typing import Pattern, Type

from ...assets.scr import Scr
from ...vfs import Resource
from ..base import BaseFormat
from .decoder import SealScrDecoder


class SealScrFormat(BaseFormat[Scr]):
  """Decoder for Seal Online `.scr` scripts (line-based text)."""

  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.scr$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Scr]:
    return Scr

  def decoder(self, res: Resource) -> Scr:
    scr = SealScrDecoder(res.open()).decode()
    scr.name = res.stem
    return scr

  def encoder(self, asset: Scr, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
