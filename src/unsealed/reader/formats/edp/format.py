import re
from pathlib import Path
from typing import Pattern, Type

from ...assets.edp import EdpArchive
from ...vfs import Resource
from ..base import BaseFormat
from .decoder import EdpDecoder


class SealEdpFormat(BaseFormat[EdpArchive]):
  """Decoder for the Seal Online `.edp` item package (`item_pak.edp`)."""

  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.edp$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[EdpArchive]:
    return EdpArchive

  def decoder(self, res: Resource) -> EdpArchive:
    return EdpDecoder(res.open()).decode()

  def encoder(self, asset: EdpArchive, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
