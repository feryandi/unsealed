from utils.file import File


class SealSprFileDecoder:
  def __init__(self, path):
    self.path = path
    self.file = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open spr file")

  def decode(self):
    """
    Decodes the SPR file and returns a list of tuples: (filename, data_bytes)
    """
    if self.file is None:
      raise Exception("File was not initialized properly")

    num_files = self.file.read_int()

    file_metadata = []
    for _ in range(num_files):
      filename = self.file.read_string(200)
      count = self.file.read_int()
      quads = []
      for _ in range(count):
        a = self.file.read_int()
        b = self.file.read_int()
        c = self.file.read_int()
        d = self.file.read_int()
        quads.append((a, b, c, d))

      file_metadata.append((filename, quads))

    return file_metadata
