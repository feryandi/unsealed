from typing import List, Optional

from .binarytree import BinaryTree
from ..core.asset import Asset


class Animation(Asset):
  def __init__(self, name, start_frame, end_frame, fps, ticks_per_frame, mesh_name):
    self.name = name
    self.start_frame = start_frame
    self.end_frame = end_frame
    self.fps = fps
    self.ticks_per_frame = ticks_per_frame
    self.mesh_name = mesh_name

    self.transforms: List[Keyframe] = []  # TODO: Rename this
    self.rotations: List[Keyframe] = []
    self.scales: List[Keyframe] = []

    self.btree: Optional[BinaryTree] = None

  def __repr__(self):
    return f"<Animation name:{self.name} start_frame:{self.start_frame} end_frame:{self.end_frame} fps:{self.fps} mesh_name:{self.mesh_name} transforms:{self.transforms} rotations:{self.rotations} scales:{self.scales}>"


class Keyframe(Asset):
  def __init__(self, time, value):
    self.time = time
    self.value = value

  def __repr__(self):
    return f"<Keyframe time:{self.time} value:{self.value} >"
