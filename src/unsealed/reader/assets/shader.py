from typing import List

from ..core.asset import Asset


class Shaders(Asset):
  def __init__(self):
    self.shaders: List[Shader] = []

  def __repr__(self) -> str:
    return f"<Shaders shaders:{self.shaders}>"


class Shader(Asset):
  def __init__(self, material_name: str, shader_name: str):
    self.material_name: str = material_name
    self.shader_name: str = shader_name
    self.sub_shaders: List[Shader] = []

  def __repr__(self) -> str:
    return (
      f"<Shader material:{self.material_name}"
      f" shader:{self.shader_name}"
      f" sub_shaders:{self.sub_shaders}>"
    )
