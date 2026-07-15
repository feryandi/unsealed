import re
from pathlib import Path
from typing import Pattern, Type

from ...assets.directory import Directory
from ...vfs import Resource
from ..base import BaseFormat
from .decoder import EdpDecoder


class SealEdpFormat(BaseFormat[Directory]):
  """Decoder for the Seal Online `.edp` EDT package (`item.edp`)."""

  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.edp$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Directory]:
    return Directory

  def decoder(self, res: Resource) -> Directory:
    return EdpDecoder(res.open()).decode()

  def encoder(self, asset: Directory, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
