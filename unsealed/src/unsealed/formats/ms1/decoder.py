from pathlib import Path
from typing import Optional

from ...utils.file import File
from ...assets.geometry import Geometry

from ..ms1.material import SealMeshMaterialDecoder
from ..ms1.geometry import SealMeshGeometryDecoder


class SealMeshDecoder:
  def __init__(self, path: Path) -> None:
    self.file: Optional[File] = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open mesh file")

  def decode(self) -> Geometry:
    if self.file is None:
      raise Exception("File was not initialized properly")
    maybe_non_first_object_has_pad = False
    maybe_different_mode = False

    ukwn = self.file.read_int()  # Unknown value
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

    geometry_decoder = SealMeshGeometryDecoder(
      self.file, maybe_non_first_object_has_pad
    )
    geometry = geometry_decoder.decode()
    for material in material_list:
      geometry.materials.append(material)

    return geometry
