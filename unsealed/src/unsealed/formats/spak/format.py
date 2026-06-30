import re
from pathlib import Path
from typing import Pattern, Type

from ..base import BaseFormat
from ...assets.directory import Directory
from ...vfs import Resource
from .decoder import SpakDecoder


class SealSpakFormat(BaseFormat[Directory]):
  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.spak$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Directory]:
    return Directory

  def decoder(self, res: Resource) -> Directory:
    # The archive opens from a real file (zipfile + raw reader); nesting
    # a .spak inside another source is unsupported.
    path = res.disk_path
    if path is None:
      raise NotImplementedError("Reading a .spak from a non-disk source")
    return SpakDecoder(path).decode()

  def encoder(self, asset: Directory, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
