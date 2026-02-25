import enum
from typing import Optional


class ResourceType(enum.Enum):
  EFFECT = 1
  FRAME = 2
  SOUND = 5
  SCRIPT = 6


class Resource:
  def __init__(self, name: Optional[str], filename: Optional[str]):
    self.name: Optional[str] = name
    self.filename: Optional[str] = filename
    self.index: int = -1
    self.type: Optional[ResourceType] = None

  def __repr__(self) -> str:
    return f"Resource(name={self.name}, \
    filename={self.filename}, type={self.type} index={self.index})"
