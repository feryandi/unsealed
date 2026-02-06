from .keyframe import Keyframe
from ..core.asset import Asset


class Animation(Asset):
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

  def add_transform_keyframe(self, keyframe: Keyframe):
    self.transforms.append(keyframe)

  def add_rotation_keyframe(self, keyframe: Keyframe):
    self.rotations.append(keyframe)

  def add_scale_keyframe(self, keyframe: Keyframe):
    self.scales.append(keyframe)

  def __repr__(self):
    return f"<Animation name:{self.name} start_frame:{self.start_frame} end_frame:{self.end_frame} fps:{self.fps} mesh_name:{self.mesh_name} transforms:{self.transforms} rotations:{self.rotations} scales:{self.scales}>"
