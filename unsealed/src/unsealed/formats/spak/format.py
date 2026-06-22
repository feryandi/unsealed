import re
from pathlib import Path
from typing import Pattern, Type

from ..base import BaseFormat
from ...assets.directory import Directory
from .decoder import SpakDecoder


class SealSpakFormat(BaseFormat[Directory]):
  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.spak$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Directory]:
    return Directory

  def decoder(self, path: Path) -> Directory:
    decoder = SpakDecoder(path)
    return decoder.decode()

  def encoder(self, asset: Directory, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
