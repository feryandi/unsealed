from core.asset import Asset


class Skeleton(Asset):
  """
  Skeletal hierarchy and Rigging.

  Handles the hierarchical relationship between bones and manages the
  global/local transform calculations for skinning.
  """

  def __init__(self):
    self.bones = []
    self.bone_name_to_id = {}

  def add_bone(self, bone):
    self.bones.append(bone)
    self.bone_name_to_id[bone.name.lower()] = len(self.bones) - 1

  def __repr__(self):
    return f"<Skeleton bones:{self.bones}>"
