from typing import Any, Dict, Optional

from ...utils.file import File, FileLike
from ...assets.skeleton import Skeleton

from ..bn1.bone import SealBoneBoneDecoder


class SealBoneDecoder:
  def __init__(self, path: FileLike) -> None:
    self.file: Optional[File] = None
    self.count: int = 0
    self.unknown: Dict[str, Any] = {}
    self.bone_decoders: list = []
    try:
      self.file = File(path)
    except Exception:
      raise Exception("Unable to open mesh file")

  def decode(self) -> Skeleton:
    if self.file is None:
      raise Exception("File was not initialized properly")

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
