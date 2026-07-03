from ...assets.shader import Shaders, Shader
from ...utils.file import File


class SealShaDecoder:
  def __init__(self, file: File) -> None:
    self.file: File = file

  def decode(self) -> Shaders:
    """Decode the SHA file into (material, shader) mappings."""
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
