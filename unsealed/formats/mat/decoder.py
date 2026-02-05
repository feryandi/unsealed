from utils.file import File


class SealMatDecoder:
  def __init__(self, path):
    self.path = path
    self.file = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open mat file")

  def decode(self):
    """
    Decodes the MAT file
    """
    if self.file is None:
      raise Exception("File was not initialized properly")

    _header = self.file.read(44)

    materials = []
    textures = []

    while self.file.is_end() is False:
      t = self.file.read_short()
      name = self.file.read_string(256)
      filename = self.file.read_string(256)

      _ = self.file.read(4)
      material_ambient = [
        self.file.read_float(),
        self.file.read_float(),
        self.file.read_float(),
      ]
      second_four = [
        self.file.read_int(),
        self.file.read_int(),
        self.file.read_int(),
        self.file.read_int(),
      ]
      x = self.file.read_int()
      material_specular = [
        self.file.read_float(),
        self.file.read_float(),
        self.file.read_float(),
      ]
      x = self.file.read_int()
      third_four = [
        self.file.read_float(),
        self.file.read_float(),
        self.file.read_float(),
        self.file.read_float(),
      ]
      x = self.file.read_float()
      self.file.read(1)
