import re
from pathlib import Path
from typing import Pattern, Type

from ...assets.tsv import Tsv
from ...vfs import Resource
from ..base import BaseFormat
from .decoder import SealTsvDecoder


class SealTsvFormat(BaseFormat[Tsv]):
  """Decoder for Seal Online `.tsv` tables (tab-delimited text)."""

  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.tsv$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Tsv]:
    return Tsv

  def decoder(self, res: Resource) -> Tsv:
    tsv = SealTsvDecoder(res.open()).decode()
    tsv.name = res.stem
    return tsv

  def encoder(self, asset: Tsv, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
