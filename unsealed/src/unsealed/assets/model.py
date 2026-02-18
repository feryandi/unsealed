from typing import Dict, List, Optional
from .skeleton import Skeleton
from .animation import Animation
from .geometry import Geometry
from ..core.asset import Asset


class Model(Asset):
  """
  High-level Model container.

  The Model class serves as the root container for complex assets,
  grouping multiple meshes, skeletons, and materials.
  """

  def __init__(self):
    self.name: Optional[str] = None
    self.geometry: Optional[Geometry] = None
    self.animations: Dict[str, List[Animation]] = {}
    self.skeleton: Optional[Skeleton] = None

  def add_geometry(self, geometry: Geometry) -> None:
    self.geometry = geometry

  def add_animation(self, name, animation: Animation) -> None:
    # TODO: Properly support multi-animation
    if name not in self.animations:
      self.animations[name] = []
    self.animations[name].append(animation)

  def add_skeleton(self, skeleton: Skeleton) -> None:
    self.skeleton = skeleton

  def __repr__(self):
    return f"<Model geometry:{self.geometry} skeleton:{self.skeleton} animations:{self.animations}>"
