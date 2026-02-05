from core.asset import Asset


class Blob(Asset):
  def __init__(self):
    self.value: bytes | None = None
    self.filename: str | None = None
    self.extension: str | None = None

  def __repr__(self):
    return f"<Blob value:{self.value}>"
