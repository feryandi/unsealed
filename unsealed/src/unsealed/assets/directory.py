from typing import List
from .blob import Blob
from ..core.asset import Asset


class Directory(Asset):
  def __init__(self):
    self.list: List[Blob] = []

  def __repr__(self):
    return f"<Directory list:{[item.filename for item in self.list]}>"
