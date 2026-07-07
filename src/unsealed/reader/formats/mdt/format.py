import re

from pathlib import Path
from typing import Pattern, Type

from ..base import BaseFormat
from ...assets.directory import Directory
from ...vfs import Resource
from ..mdt.decoder import SealMdtDecoder


class SealMdtFormat(BaseFormat[Directory]):
  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.mdt$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Directory]:
    return Directory

  def decoder(self, res: Resource) -> Directory:
    decoder = SealMdtDecoder(res.open())
    blobs = decoder.decode()
    return blobs

  def encoder(self, asset: Directory, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
