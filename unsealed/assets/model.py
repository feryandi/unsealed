from core.asset import Asset
from assets.animation import Animation
from assets.geometry import Geometry


class Model(Asset):
  """
  High-level Model container.

  The Model class serves as the root container for complex assets,
  grouping multiple meshes, skeletons, and materials.
  """

  def __init__(self):
    self.geometry = None
    self.animations = {}
    self.skeleton = None

  def add_geometry(self, geometry: Geometry):
    self.geometry = geometry

  def add_animation(self, name, animation: Animation):
    # TODO: Properly support multi-animation
    if name not in self.animations:
      self.animations[name] = []
    self.animations[name].append(animation)

  def add_skeleton(self, skeleton):
    self.skeleton = skeleton

  def __repr__(self):
    return f"<Model geometry:{self.geometry} skeleton:{self.skeleton} animations:{self.animations}>"
