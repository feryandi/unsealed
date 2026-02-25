
from abc import ABC
from typing import Any, Dict


class Asset(ABC):
  """Base class for all intermediate representations"""

  def __init__(self) -> None:
    self.metadata: Dict[str, Any] = {}
