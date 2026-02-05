from assets.blob import Blob
from assets.directory import Directory
from utils.file import File


class SealMdtDecoder:
  def __init__(self, path):
    self.path = path
    self.file = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open mdt file")

  def decode(self) -> Directory:
    """
    Decodes the MDT file and returns a list of blob: (filename, data_bytes)
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
      blob = Blob()
      blob.value = self.file.read(size)
      blob.filename = filename.split(".")[0]
      blob.extension = filename.split(".")[1]
      decoded_files.append(blob)

    dir = Directory()
    dir.list = decoded_files
    return dir
