import re
from pathlib import Path
from typing import Pattern, Type

from ...assets.dat import DatFile
from ...vfs import Resource
from ..base import BaseFormat
from .decoder import SealDatDecoder


class SealDatFormat(BaseFormat[DatFile]):
  """Decoder for Seal Online `.dat` data files (header + records)."""

  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.dat$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[DatFile]:
    return DatFile

  def decoder(self, res: Resource) -> DatFile:
    return SealDatDecoder(res.open()).decode()

  def encoder(self, asset: DatFile, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
