from pathlib import Path
from typing import Any, Dict, Optional

from ...assets.shader import Shaders, Shader
from ...utils.file import File


class SealShaDecoder:
  def __init__(self, path: Path) -> None:
    self.path: Path = path
    self.file: Optional[File] = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open sha file")

  def decode(self) -> Shaders:
    """
    Decodes the SHA file and returns a list of tuples: (material, shader)
    """
    if self.file is None:
      raise Exception("File was not initialized properly")

    shaders = Shaders()
    num_entries = self.file.read_int()

    for _ in range(num_entries):
      material_name = self.file.read_string(128)
      shader_name = self.file.read_string(128)
      sub_material_num = self.file.read_int()
      shader = Shader(material_name, shader_name)

      for _ in range(sub_material_num):
        sub_material_name = self.file.read_string(128)
        shader_name = self.file.read_string(128)
        shader.sub_shaders.append(Shader(sub_material_name, shader_name))

      shaders.shaders.append(shader)

    return shaders
