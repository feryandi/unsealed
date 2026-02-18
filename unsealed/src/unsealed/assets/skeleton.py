from typing import Dict, Optional
from ..core.asset import Asset


class Skeleton(Asset):
  """
  Skeletal hierarchy and Rigging.

  Handles the hierarchical relationship between bones and manages the
  global/local transform calculations for skinning.
  """

  def __init__(self):
    self.bones: Dict[str, Bone] = {}

  def __repr__(self):
    return f"<Skeleton bones:{self.bones}>"


class Bone(Asset):
  """
  Bone intermediate representation.

  This module defines the data structure for individual bones used in
  skeletal animations.
  """

  def __init__(self):
    self.count: int = 0
    self.name: str = ""
    self.parent: Optional[str] = None

    self.tm = [
      [1.0, 0.0, 0.0, 0.0],
      [0.0, 1.0, 0.0, 0.0],
      [0.0, 0.0, 1.0, 0.0],
      [0.0, 0.0, 0.0, 1.0],
    ]
    self.tm_inverse = [
      [1.0, 0.0, 0.0, 0.0],
      [0.0, 1.0, 0.0, 0.0],
      [0.0, 0.0, 1.0, 0.0],
      [0.0, 0.0, 0.0, 1.0],
    ]

    self.loc = [0.0, 0.0, 0.0]
    self.sca = [1.0, 1.0, 1.0]
    self.rot = [0.0, 0.0, 0.0, 1.0]

  def __repr__(self):
    return f"<Bone name:{self.name} parent:{self.parent}>"
