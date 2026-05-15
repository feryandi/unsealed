from typing import Optional
from ..core.asset import Asset


class Blob(Asset):
  def __init__(self) -> None:
    self.value: Optional[bytes] = None  # opaque encoded bytes (PNG/DDS/raw…)
    self.name: Optional[str] = None
    self.extension: Optional[str] = None
    # Optional fast path: pre-decoded RGBA pixels + dimensions. When set,
    # in-process consumers can skip the PIL decode of `value`. Producers
    # (e.g. SealSprFormat) populate these and leave `value` as None so the
    # round-trip PNG encode/decode is avoided entirely.
    self.image_rgba: Optional[bytes] = None
    self.width: int = 0
    self.height: int = 0

  def __repr__(self) -> str:
    if self.image_rgba is not None:
      return f"<Blob rgba {self.width}x{self.height}>"
    return f"<Blob value:{self.value}>"
