
from abc import ABC


class Asset(ABC):
  """Base class for all intermediate representations"""

  def __init__(self):
    self.metadata = {}
