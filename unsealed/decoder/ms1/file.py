from file import File
from utils.strings import is_valid_ascii_letter

from decoder.ms1.material import SealMeshMaterialDecoder
from decoder.ms1.geometry import SealMeshGeometryDecoder


class SealMeshFileDecoder:
  def __init__(self, path):
    self.file = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except:
      raise Exception("Unable to open mesh file")

  def decode(self):
    if self.file is None:
      raise Exception("No file loaded")
    maybe_non_first_object_has_pad = False
    maybe_different_mode = False

    ukwn = self.file.read_int() # Unknown value
    if ukwn == 0:
      # Normal mode
      pass
    if ukwn == 1:
      maybe_non_first_object_has_pad = True
    if ukwn == 10:
      # T_Gube1_idle, T_Gube2_idle, T_Gube3_idle, and several other skills
      maybe_different_mode = True

    materials_decoder = SealMeshMaterialDecoder(self.file, maybe_different_mode)
    material_list = materials_decoder.decode()

    geometry_decoder = SealMeshGeometryDecoder(self.file, maybe_non_first_object_has_pad)
    geometry = geometry_decoder.decode()
    for material in material_list:
      geometry.add_material(material)

    return geometry

