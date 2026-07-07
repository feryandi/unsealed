from typing import Dict, List, Optional
from ..core.asset import Asset


class Skeleton(Asset):
  """
  Skeletal hierarchy and Rigging.

  Handles the hierarchical relationship between bones and manages the
  global/local transform calculations for skinning.
  """

  def __init__(self) -> None:
    self.bones: Dict[str, Bone] = {}

  def __repr__(self) -> str:
    return f"<Skeleton bones:{self.bones}>"


class Bone(Asset):
  """
  Bone intermediate representation.

  This module defines the data structure for individual bones used in
  skeletal animations.
  """

  def __init__(self) -> None:
    self.count: int = 0
    self.name: str = ""
    self.parent: Optional[str] = None

    self.tm: List[List[float]] = [
      [1.0, 0.0, 0.0, 0.0],
      [0.0, 1.0, 0.0, 0.0],
      [0.0, 0.0, 1.0, 0.0],
      [0.0, 0.0, 0.0, 1.0],
    ]
    self.tm_inverse: List[List[float]] = [
      [1.0, 0.0, 0.0, 0.0],
      [0.0, 1.0, 0.0, 0.0],
      [0.0, 0.0, 1.0, 0.0],
      [0.0, 0.0, 0.0, 1.0],
    ]

    self.loc: List[float] = [0.0, 0.0, 0.0]
    self.sca: List[float] = [1.0, 1.0, 1.0]
    self.rot: List[float] = [0.0, 0.0, 0.0, 1.0]

  def __repr__(self) -> str:
    return f"<Bone name:{self.name} parent:{self.parent}>"
