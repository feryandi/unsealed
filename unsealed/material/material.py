
class Material:
  def __init__(self, name, bitmap):
    self.name = name
    self.bitmap = bitmap
    self.num_sub_material = 0
    self.sub_materials = []
    self.size = 0
    self.enabled = False
    self.alpha_mode = 0

  def add_sub_material(self, material):
    self.sub_materials.append(material)
    self.size += material.size

  def set_enabled(self, enabled):
    self.enabled = enabled

  def __repr__(self):
    return f"<Material name:{self.name} bitmap:{self.bitmap} sub_materials:{self.sub_materials}>"
