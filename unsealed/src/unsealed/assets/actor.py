from typing import List, Optional
from .resource import Resource


class Actor:
  def __init__(self, name: str, filename: str):
    self.name: str = name
    self.filename: str = filename
    self.actions: List[Action] = []


class Action:
  def __init__(self, name: Optional[str], filename: str):
    self.name: Optional[str] = name
    self.filename: str = filename
    self.resources: List[Resource] = []

  def __repr__(self):
    return (
      f"Action(name={self.name}, filename={self.filename}, resources={self.resources})"
    )
