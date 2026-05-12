from typing import List, Optional, Self
from ..core.asset import Asset


class Material(Asset):
  """
  Material and Shading intermediate representation.

  Provides structures for material properties, texture maps, and surface
  attribute configurations for rendering.
  """

  def __init__(self, name: str, bitmap: str) -> None:
    self.name: str = name
    self.bitmap: str = bitmap
    self.num_sub_material: int = 0
    self.sub_materials: List[Self] = []
    self.alpha_mode: int = 0
    self.material_ambient: List[float] = [0.0, 0.0, 0.0]
    self.material_diffuse: List[float] = [0.0, 0.0, 0.0]
    self.material_specular: List[float] = [0.0, 0.0, 0.0]
    self.shader_name: Optional[str] = None

  def __repr__(self) -> str:
    return (
      f"<Material name:{self.name}"
      f" bitmap:{self.bitmap}"
      f" shader_name:{self.shader_name}>"
      f" sub_materials:{self.sub_materials}"
      f" alpha_mode:{self.alpha_mode}"
      f" material_ambient:{self.material_ambient}"
      f" material_diffuse:{self.material_diffuse}"
      f" material_specular:{self.material_specular}>"
    )
