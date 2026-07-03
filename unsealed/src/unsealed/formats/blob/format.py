import re

from pathlib import Path
from typing import Pattern, Type

from ..base import BaseFormat
from ...assets.blob import Blob
from ...vfs import Resource
from ..blob.decoder import BlobDecoder


class BlobFormat(BaseFormat[Blob]):
  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.[^.]+$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Blob]:
    return Blob

  def decoder(self, res: Resource) -> Blob:
    decoder = BlobDecoder(res.open())
    return decoder.decode()

  def encoder(self, asset: Blob, path: Path) -> None:
    if asset.value is not None:
      if path.is_dir():
        filename = f"{asset.name}.{asset.extension}"
        with open(path / filename, "wb") as f:
          f.write(asset.value)
      else:
        filename = path.name
        if not filename:
          filename = f"{asset.name}.{asset.extension}"
        if not path.suffix:
          filename = f"{filename}.{asset.extension}"
        with open(path.with_name(filename), "wb") as f:
          f.write(asset.value)
    else:
      raise Exception("Encoder failed: nothing to write")
