import re
from pathlib import Path
from typing import Pattern, Type

from ...assets.eddb import ItemDb
from ...vfs import Resource
from ..base import BaseFormat
from .decoder import ItemDbDecoder


class SealItemDbFormat(BaseFormat[ItemDb]):
  """Decoder for Seal Online item-database shards (`.ed1`, `.ed2`, …)."""

  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.ed\d+$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[ItemDb]:
    return ItemDb

  def decoder(self, res: Resource) -> ItemDb:
    return ItemDbDecoder(res.open()).decode()

  def encoder(self, asset: ItemDb, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
