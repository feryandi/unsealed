import numpy as np
import mathutils

from file import File

from skeleton.bone import Bone


class SealBoneBoneDecoder:
  def __init__(self, file):
    self.file = file

  def decode(self):
    bone = Bone()
    bone.name = self.file.read_string(256)
    t = self.file.read(1)

    if t == b'\x01':
      bone.parent = self.file.read_string(256)
    else:
      _ = self.file.read(256)
    
    cc = [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()]
    self.__decode_data(bone)
    return bone

  def __decode_data(self, bone):
    bone.tm = [
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
    ]
    bone.tm_inverse = [
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
    ]
    _ = [
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
      [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()],
    ]
    broken_loc = [self.file.read_float(), self.file.read_float(), self.file.read_float()]
    broken_sca = [self.file.read_float(), self.file.read_float(), self.file.read_float()]
    broken_rot = [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()]

    ntm = np.array(bone.tm).T
    tm = mathutils.Matrix(ntm)
    loc, rot, sca = tm.decompose()
    bone.loc = [loc.x, loc.y, loc.z]
    bone.rot = [rot.w, rot.x, rot.y, rot.z]
    bone.sca = [sca.x, sca.y, sca.z]

    itm = np.array(bone.tm_inverse).T
    # Fix the tm_inverse
    intm = np.array(tm.inverted()).T
    bone.tm_inverse = intm.tolist()

    _ = [self.file.read_float(), self.file.read_float(), self.file.read_float(), self.file.read_float()]
