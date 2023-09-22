from material.material import Material


class SealMeshMaterialDecoder:
  def __init__(self, file, different_mode):
    self.file = file
    self.count = 0
    self.different_mode = different_mode

  def decode(self):
    materials = []
    self.count = self.file.read_int()
    for x in range(self.count):
      if not self.different_mode:
        material = self.__decode_normal_material()
        # These data block is not available on sub-material
        pad = 16 + 4 + 5
        _ = self.file.read_float() # Unknown value of Kd, Ks, ?
        _ = self.file.read_float() # Unknown value of Kd, Ks, ?
        _ = self.file.read_float() # Unknown value of Kd, Ks, ?
        _ = self.file.read(pad) # Unknown value of Kd, Ks, ?
        materials.append(material)
      else:
        while self.__is_still_material(self.file):
          material = self.__decode_special_material()
          materials.append(material)
    return materials

  def __decode_normal_material(self):
    _ = self.file.read_short()
    bitmap = self.file.read_string(256)
    name = self.file.read_string(128)
    material = Material(name, bitmap)

    _ = self.file.read_string(128)
    num_sub_material = self.file.read_int()
    
    _ = self.file.read_float() # Probably: Material Ambient or/and Diffuse (YES!)
    _ = self.file.read_float() # Probably: Material Ambient or/and Diffuse (YES!)
    _ = self.file.read_float() # Probably: Material Ambient or/and Diffuse (YES!)
    _ = self.file.read_float() # Dunno
    _ = self.file.read(16) # Name?

    for y in range(num_sub_material):
      pad = 16 + 16 + 5
      _ = self.file.read(pad)
      submaterial = self.__decode_normal_material()
      material.add_sub_material(submaterial)
    return material

  def __decode_special_material(self):
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
    if check == b'\x2D\x01\x00\x00':
      pad = self.file.read_int()
      self.file.read(pad*4)
      if self.file.seek(4) == b'\x2D\x01\x00\x00':
        self.file.read(pad*16)
        _ = self.file.read(16)
      _ = self.file.read(8)
    elif check == b'\x57\x00\x00\x00':
      pad = self.file.read_int()
      self.file.read(22*16-4)
      i = 0
      if self.file.seek(4) == b'\x57\x00\x00\x00':
        i += 1
        self.file.read(86*16+8)
        _ = self.file.read(12)
      if self.file.seek(4) == b'\x57\x00\x00\x00':
        i += 1
        self.file.read(86*16+8)
        _ = self.file.read(4)
      _ = self.file.read(8)
      if i == 1:
        self.file.read(12)
    elif check == b'\x75\x00\x00\x00':
      pad = 30 * 16
      self.file.read(pad)
      if self.file.seek(1) == b'\x00':
        self.file.read(32)
    elif check == b'\x00\x00\x00\x00':
      self.file.read(4)
      pad = self.file.read_int()
      _ = self.file.read(4)
      self.file.read(pad*16)
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
  def __is_still_material(self):
    check = self.file.seek(6)
    if is_valid_ascii_letter(check[2]):
      return True
    if not is_valid_ascii_letter(check[2]) and not is_valid_ascii_letter(check[3]):
      if is_valid_ascii_letter(check[4]):
        return False
      return True
    return False


