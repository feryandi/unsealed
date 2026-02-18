from typing import Optional
from ..core.asset import Asset


class Blob(Asset):
  def __init__(self):
    self.value: Optional[bytes] = None
    self.filename: Optional[str] = None
    self.extension: Optional[str] = None

  def __repr__(self):
    return f"<Blob value:{self.value}>"
