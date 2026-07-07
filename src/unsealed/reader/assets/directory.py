from typing import List
from .blob import Blob
from ..core.asset import Asset


class Directory(Asset):
  def __init__(self, name="Untitled") -> None:
    self.name: str = name
    self.list: List[Blob | Directory] = []

  def __repr__(self) -> str:
    return f"<Directory list:{[item.name for item in self.list]}>"
