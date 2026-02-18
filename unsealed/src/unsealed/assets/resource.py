from typing import Optional


class Resource:
  def __init__(self, name: Optional[str], filename: Optional[str]):
    self.name: Optional[str] = name
    self.filename: Optional[str] = filename
