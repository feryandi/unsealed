from typing import List
from core.asset import Asset
from assets.blob import Blob


class Directory(Asset):
  def __init__(self):
    self.list: List[Blob] = []

  def __repr__(self):
    return f"<Directory list:{[item.filename for item in self.list]}>"
