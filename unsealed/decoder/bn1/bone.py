import numpy as np

from utils.file import File
from utils.matrix import decompose_mtx

from model.bone import Bone


class SealBoneBoneDecoder:
  def __init__(self, file: File):
    self.file = file

  def decode(self):
    bone = Bone()
    bone.name = self.file.read_string(256)
    t = self.file.read(1)

    if t == b'\x01':
      bone.parent = self.file.read_string(256)
    else:
      _ = self.file.read(256)

    cc = [self.file.read_float(), self.file.read_float(
    ), self.file.read_float(), self.file.read_float(), self.file.read_float()]
    self.__decode_data(bone)
    return bone

  def __decode_data(self, bone):
    bone.tm = [
        [self.file.read_float(), self.file.read_float(),
         self.file.read_float(), self.file.read_float()],
        [self.file.read_float(), self.file.read_float(),
         self.file.read_float(), self.file.read_float()],
        [self.file.read_float(), self.file.read_float(),
         self.file.read_float(), self.file.read_float()],
        [self.file.read_float(), self.file.read_float(),
         self.file.read_float(), self.file.read_float()],
    ]
    bone.tm_inverse = [
        [self.file.read_float(), self.file.read_float(),
         self.file.read_float(), self.file.read_float()],
        [self.file.read_float(), self.file.read_float(),
         self.file.read_float(), self.file.read_float()],
        [self.file.read_float(), self.file.read_float(),
         self.file.read_float(), self.file.read_float()],
        [self.file.read_float(), self.file.read_float(),
         self.file.read_float(), self.file.read_float()],
    ]
    _ = [
        [self.file.read_float(), self.file.read_float(),
         self.file.read_float(), self.file.read_float()],
        [self.file.read_float(), self.file.read_float(),
         self.file.read_float(), self.file.read_float()],
        [self.file.read_float(), self.file.read_float(),
         self.file.read_float(), self.file.read_float()],
    ]
    broken_loc = [self.file.read_float(), self.file.read_float(),
                  self.file.read_float()]
    broken_sca = [self.file.read_float(), self.file.read_float(),
                  self.file.read_float()]
    broken_rot = [self.file.read_float(), self.file.read_float(
    ), self.file.read_float(), self.file.read_float()]

    ntm = np.array(bone.tm).T
    tm = np.array(ntm)
    loc, rot, sca = decompose_mtx(tm)
    bone.loc = [loc[0], loc[1], loc[2]]
    bone.rot = [rot[0], rot[1], rot[2], rot[3]]
    bone.sca = [sca[0], sca[1], sca[2]]

    itm = np.array(bone.tm_inverse).T
    intm = np.linalg.inv(tm).T
    bone.tm_inverse = intm.tolist()

    _ = [self.file.read_float(), self.file.read_float(
    ), self.file.read_float(), self.file.read_float()]
