from ...utils.file import File


class SealShaDecoder:
  def __init__(self, path):
    self.path = path
    self.file = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open sha file")

  def decode(self):
    """
    Decodes the SHA file and returns a list of tuples: (material, shader)
    """
    if self.file is None:
      raise Exception("File was not initialized properly")

    num_entries = self.file.read_int()

    shaders = {}
    for _ in range(num_entries):
      material = self.file.read_string(128)
      shader = self.file.read_string(128)
      sub_material_num = self.file.read_int()
      item = {
        "shader": shader,
        "sub_materials": {},
      }
      for _ in range(sub_material_num):
        sub_material = self.file.read_string(128)
        shader = self.file.read_string(128)
        item["sub_materials"][sub_material] = {"shader": shader}
      shaders[material] = item
    return shaders
