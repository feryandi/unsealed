from pathlib import Path
from typing import Any, Dict, Optional

from ...utils.file import File
from ...assets.geometry import Geometry

from ..ms1.material import SealMeshMaterialDecoder
from ..ms1.geometry import SealMeshGeometryDecoder


class SealMeshDecoder:
  def __init__(self, path: Path) -> None:
    self.file: Optional[File] = None
    self.unknown: Dict[str, Any] = {}
    self.material_decoder: Optional[SealMeshMaterialDecoder] = None
    self.geometry_decoder: Optional[SealMeshGeometryDecoder] = None
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

    ukwn = self.file.read_int()
    self.unknown["header_ukwn"] = ukwn
    if ukwn == 1:
      maybe_non_first_object_has_pad = True
    elif ukwn == 10:
      # T_Gube1_idle, T_Gube2_idle, T_Gube3_idle, and several other skills
      maybe_different_mode = True

    self.material_decoder = SealMeshMaterialDecoder(self.file, maybe_different_mode)
    material_list = self.material_decoder.decode()

    self.geometry_decoder = SealMeshGeometryDecoder(
      self.file, maybe_non_first_object_has_pad
    )
    geometry = self.geometry_decoder.decode()
    geometry.materials.extend(material_list)

    return geometry
