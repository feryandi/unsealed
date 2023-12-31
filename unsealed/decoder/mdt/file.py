import io
import os
import struct

from file import File


class SealMdtFileDecoder:
  def __init__(self, path, output_path):
    self.path = path
    self.file = None
    self.output_path = output_path
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except:
      raise Exception("Unable to open mdt file")

  def decode(self):
    num_files = self.file.read_int()

    filenames = []
    sizes = []
    for n in range(num_files):
      filename = self.file.read_string(16 * 6)
      filenames.append(filename)
      _ = self.file.read(4)
      size = self.file.read_int()
      sizes.append(size)
      start = self.file.read(4)  # need to + 4 the value

    for idx, filename in enumerate(filenames):
      size = sizes[idx]
      with open(self.output_path + "/" + filename, "wb") as f:
        f.write(self.file.read(size))
    