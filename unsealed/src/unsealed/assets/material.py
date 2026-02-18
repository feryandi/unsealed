from typing import List, Self
from ..core.asset import Asset


class Material(Asset):
  """
  Material and Shading intermediate representation.

  Provides structures for material properties, texture maps, and surface
  attribute configurations for rendering.
  """

  def __init__(self, name: str, bitmap: str):
    self.name = name
    self.bitmap = bitmap
    self.num_sub_material = 0
    self.sub_materials: List[Self] = []
    self.alpha_mode = 0

  def __repr__(self):
    return f"<Material name:{self.name} bitmap:{self.bitmap} sub_materials:{self.sub_materials}>"
