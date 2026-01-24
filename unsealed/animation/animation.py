
class Animation:
  def __init__(self, name, start_frame, end_frame, fps, mesh_name):
    self.smallest_keyframe = 160.0  # TODO

    self.name = name
    self.start_frame = start_frame
    self.end_frame = end_frame
    self.fps = fps
    self.mesh_name = mesh_name

    self.transforms = []  # TODO: Rename this
    self.rotations = []
    self.scales = []

  def add_transform_keyframe(self, keyframe):
    self.transforms.append(keyframe)

  def add_rotation_keyframe(self, keyframe):
    self.rotations.append(keyframe)

  def add_scale_keyframe(self, keyframe):
    self.scales.append(keyframe)
