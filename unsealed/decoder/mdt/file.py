import io
import os
import struct

from utils.file import File


class SealMdtFileDecoder:
  def __init__(self, path):
    self.path = path
    self.file = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open mdt file")

  def decode(self):
    """
    Decodes the MDT file and returns a list of tuples: (filename, data_bytes)
    """
    if self.file is None:
      raise Exception("File was not initialized properly")

    num_files = self.file.read_int()

    file_metadata = []
    for _ in range(num_files):
      filename = self.file.read_string(16 * 6)
      _ = self.file.read(4)
      size = self.file.read_int()
      _ = self.file.read(4)  # Skip the start offset pointer
      file_metadata.append((filename, size))

    decoded_files = []
    for filename, size in file_metadata:
      # Read the actual byte data from the stream
      file_data = self.file.read(size)
      decoded_files.append((filename, file_data))

    return decoded_files
