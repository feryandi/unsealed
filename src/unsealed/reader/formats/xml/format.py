import re
from pathlib import Path
from typing import Pattern, Type

from ...assets.xml import Xml
from ...vfs import Resource
from ..base import BaseFormat
from .decoder import SealXmlDecoder


class SealXmlFormat(BaseFormat[Xml]):
  """Decoder for Seal Online `.xml` data tables (self-describing rows)."""

  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.xml$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Xml]:
    return Xml

  def decoder(self, res: Resource) -> Xml:
    xml = SealXmlDecoder(res.open()).decode()
    xml.name = res.stem
    return xml

  def encoder(self, asset: Xml, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
