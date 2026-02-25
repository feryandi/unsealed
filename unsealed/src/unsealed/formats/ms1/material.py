from typing import List

from ...utils.file import File
from ...utils.strings import is_valid_ascii_letter
from ...assets.material import Material


class SealMeshMaterialDecoder:
  def __init__(self, file: File, different_mode: bool) -> None:
    self.file: File = file
    self.count: int = 0
    self.different_mode: bool = different_mode

  def decode(self) -> List[Material]:
    if self.different_mode:
      print("Warning: Material is in different_mode")

    materials = []
    self.count = self.file.read_int()
    for x in range(self.count):
      if not self.different_mode:
        material = self.__decode_normal_material()
        # These data block is not available on sub-material
        _x = [
          self.file.read_float(),
          self.file.read_float(),
          self.file.read_float(),
          self.file.read_float(),
          self.file.read_float(),
          self.file.read_float(),
          self.file.read_float(),
          self.file.read_float(),
          self.file.read_float(),
        ]
        alpha_mode = self.file.read(1)
        material.alpha_mode = int.from_bytes(alpha_mode, byteorder="little")

        materials.append(material)
      else:
        while self.__is_still_material():
          material = self.__decode_special_material()
          materials.append(material)
    return materials

  def __decode_normal_material(self) -> Material:
    _x = self.file.read_short()
    bitmap = self.file.read_string(256)
    name = self.file.read_string(128)
    material = Material(name, bitmap)

    _x = self.file.read_string(128)
    num_sub_material = self.file.read_int()
    _x = [
      self.file.read_float(),
      self.file.read_float(),
      self.file.read_float(),
      self.file.read_float(),
      self.file.read_float(),
      self.file.read_float(),
      self.file.read_float(),
      self.file.read_float(),
    ]

    for y in range(num_sub_material):
      _x = [
        self.file.read_float(),
        self.file.read_float(),
        self.file.read_float(),
        self.file.read_float(),
      ]
      _x = [
        self.file.read_float(),
        self.file.read_float(),
        self.file.read_float(),
        self.file.read_float(),
      ]
      _x = self.file.read(5)
      submaterial = self.__decode_normal_material()
      material.sub_materials.append(submaterial)
    return material

  def __decode_special_material(self) -> Material:
    # Unknown what special about this, yet
    _ = self.file.read_short()
    bitmap = self.file.read_string(256)
    _ = self.file.read_string(256)
    _ = self.file.read(16)

    pad = 0

    # Hacky logic
    # 01 00 01 00 05 00 06 00 04 00 04 00 FF FF FF FF -- Prop_Stuff
    # 01 00 01 00 05 00 06 00 04 00 04 00 FF FF FF FF -- Archi Portal
    # 01 00 01 00 05 00 02 00 04 00 04 00 FF FF FF FF 2D 01 -- Dragon .. Depends if repeat
    # 03 00 01 00 05 00 06 00 04 00 04 00 FF FF FF FF 75 -- Samael .. 30 block + 15 bytes
    # 01 00 01 00 05 00 02 00 04 00 04 00 FF FF FF FF 00 00 00 00 size
    check = self.file.seek(4)
    if check == b"\x2d\x01\x00\x00":
      pad = self.file.read_int()
      self.file.read(pad * 4)
      if self.file.seek(4) == b"\x2d\x01\x00\x00":
        self.file.read(pad * 16)
        _ = self.file.read(16)
      _ = self.file.read(8)
    elif check == b"\x57\x00\x00\x00":
      pad = self.file.read_int()
      self.file.read(22 * 16 - 4)
      i = 0
      if self.file.seek(4) == b"\x57\x00\x00\x00":
        i += 1
        self.file.read(86 * 16 + 8)
        _ = self.file.read(12)
      if self.file.seek(4) == b"\x57\x00\x00\x00":
        i += 1
        self.file.read(86 * 16 + 8)
        _ = self.file.read(4)
      _ = self.file.read(8)
      if i == 1:
        self.file.read(12)
    elif check == b"\x75\x00\x00\x00":
      pad = 30 * 16
      self.file.read(pad)
      if self.file.seek(1) == b"\x00":
        self.file.read(32)
    elif check == b"\x00\x00\x00\x00":
      self.file.read(4)
      pad = self.file.read_int()
      _ = self.file.read(4)
      self.file.read(pad * 16)
    else:
      pad = self.file.read_int()
      self.file.read(pad * 4)
      _ = self.file.read(8)

    name = self.file.read_string(256)
    material = Material(name, bitmap)
    _ = self.file.read_int()
    _ = self.file.read(16 * 4)
    _ = self.file.read(5)
    return material

  # Hacky and might not work :(
  def __is_still_material(self) -> bool:
    check = self.file.seek(6)
    if is_valid_ascii_letter(check[2]):
      return True
    if not is_valid_ascii_letter(check[2]) and not is_valid_ascii_letter(check[3]):
      if is_valid_ascii_letter(check[4]):
        return False
      return True
    return False
