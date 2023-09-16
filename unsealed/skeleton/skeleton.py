
class Skeleton:
  def __init__(self):
    self.bones = []
    self.bone_name_to_id = {}
    self.bone_name_to_node_idx = {} # TODO: Put this on encoder

  def add_bone(self, bone):
    self.bones.append(bone)
    self.bone_name_to_id[bone.name.lower()] = len(self.bones) - 1
