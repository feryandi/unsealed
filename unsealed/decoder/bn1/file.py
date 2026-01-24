from utils.file import File
from model.skeleton import Skeleton

from decoder.bn1.bone import SealBoneBoneDecoder


class SealBoneFileDecoder:
  def __init__(self, path):
    self.file = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except:
      raise Exception("Unable to open mesh file")

  def decode(self):
    if self.file is None:
      raise Exception("File was not initialized properly")

    skeleton = Skeleton()
    _ = self.file.read(4)
    _ = self.file.read(4)
    self.count = self.file.read_int()

    for i in range(self.count):
      decoder = SealBoneBoneDecoder(self.file)
      bone = decoder.decode()
      skeleton.add_bone(bone)

    return skeleton
