from typing import Optional

from ...assets.shader import Shaders, Shader
from ...utils.file import File, FileLike


class SealShaDecoder:
  def __init__(self, path: FileLike) -> None:
    self.path: FileLike = path
    self.file: Optional[File] = None
    try:
      self.file = File(path)
    except Exception:
      raise Exception("Unable to open sha file")

  def decode(self) -> Shaders:
    """Decode the SHA file into (material, shader) mappings."""
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
