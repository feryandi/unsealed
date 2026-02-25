from pathlib import Path
from typing import List, Optional

from .binarytree import BinaryTree
from ..core.asset import Asset


class Animation(Asset):
  def __init__(
    self,
    name: Path,
    start_frame: int,
    end_frame: int,
    fps: float,
    ticks_per_frame: float,
    mesh_name: str,
  ) -> None:
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

  def __repr__(self) -> str:
    return f"<Animation name:{self.name} start_frame:{self.start_frame} end_frame:{self.end_frame} fps:{self.fps} mesh_name:{self.mesh_name} transforms:{self.transforms} rotations:{self.rotations} scales:{self.scales}>"


class Keyframe(Asset):
  def __init__(self, time: int, value: List[float]) -> None:
    self.time = time
    self.value = value

  def __repr__(self) -> str:
    return f"<Keyframe time:{self.time} value:{self.value} >"
