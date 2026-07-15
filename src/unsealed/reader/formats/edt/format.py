import re

from pathlib import Path
from typing import Pattern, Type

from ..base import BaseFormat
from ...assets.edt import Edt
from ...vfs import Resource
from .decoder import EdtDecoder
from .codec import encode


class SealEdtFormat(BaseFormat[Edt]):
  """Decoder/encoder for Seal Online `.edt` (LCG stream cipher).

  Also claims the item-db shards (`.ed1` … `.ed<n>`): they are the same
  cipher and the same container, differing only in what the plaintext
  turns out to be (a headerless ItemFile band — see `band.py`).
  """

  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.(edt|ed\d+)$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Edt]:
    return Edt

  def decoder(self, res: Resource) -> Edt:
    return EdtDecoder(res.open()).decode()

  def encoder(self, asset: Edt, path: Path) -> None:
    if asset.value is None:
      raise Exception("Encoder failed: nothing to write")

    encoded = encode(asset.value)
    name = asset.name or "output"

    if path.is_dir():
      target = path / f"{name}.edt"
    else:
      target = path
      if not target.suffix:
        target = target.with_suffix(".edt")

    with open(target, "wb") as f:
      f.write(encoded)
