from typing import Any, Dict

from ...utils.file import File
from ...assets.skeleton import Skeleton

from ..bn1.bone import SealBoneBoneDecoder


class SealBoneDecoder:
  def __init__(self, file: File) -> None:
    self.file: File = file
    self.count: int = 0
    self.unknown: Dict[str, Any] = {}
    self.bone_decoders: list = []

  def decode(self) -> Skeleton:
    skeleton = Skeleton()
    self.unknown["header_a"] = self.file.read(4)
    self.unknown["header_b"] = self.file.read(4)
    self.count = self.file.read_int()

    for _ in range(self.count):
      decoder = SealBoneBoneDecoder(self.file)
      self.bone_decoders.append(decoder)
      bone = decoder.decode()
      skeleton.bones[bone.name] = bone

    return skeleton
