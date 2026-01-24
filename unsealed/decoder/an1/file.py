from utils.file import File
from animation.animation import Animation
from animation.keyframe import Keyframe


class SealAnimationFileDecoder:
  def __init__(self, path):
    self.path = path
    self.file = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except:
      raise Exception("Unable to open mesh file")

  def decode(self):
    if self.file is None:
      raise Exception("File was not initialized properly")
    animations = []
    start_frame = self.file.read_int()
    end_frame = self.file.read_int()
    fps = self.file.read_float()

    _ = self.file.read(4)
    # Padded string space
    _ = self.file.read(17 * 16)

    self.nodes = self.file.read_int()

    for i in range(self.nodes):
      name = self.file.read_string(256)
      # TODO: Change the name to a better one?
      node = Animation(self.path, start_frame, end_frame, fps, name)

      self.__decode_position(node)
      self.__decode_rotation(node)
      self.__decode_scale(node)

      animations.append(node)
    return animations

  def __decode_position(self, node):
    assert self.file is not None, "File was not initialized properly"
    size = self.file.read_int()

    for j in range(size):
      time = self.file.read_int()
      x = self.file.read_float()
      y = self.file.read_float()
      z = self.file.read_float()
      position = [x, y, z]
      keyframe = Keyframe(time, position)
      node.add_transform_keyframe(keyframe)
      _ = self.file.read(8)  # TODO
    if size != 0:
      hash_num = self.file.read_int()

  def __decode_rotation(self, node):
    assert self.file is not None, "File was not initialized properly"
    size = self.file.read_int()

    for j in range(size):
      time = self.file.read_int()
      x = self.file.read_float()
      y = self.file.read_float()
      z = self.file.read_float()
      w = self.file.read_float()
      rotation = [x, y, z, w]
      keyframe = Keyframe(time, rotation)
      node.add_rotation_keyframe(keyframe)
      _ = self.file.read(16 + 8)  # TODO

    if size != 0:
      hash_num = self.file.read_int()

  def __decode_scale(self, node):
    assert self.file is not None, "File was not initialized properly"
    size = self.file.read_int()

    for j in range(size):
      time = self.file.read_int()
      x = self.file.read_float()
      y = self.file.read_float()
      z = self.file.read_float()
      scale = [x, y, z]
      keyframe = Keyframe(time, scale)
      node.add_scale_keyframe(keyframe)
      _ = self.file.read(16 + 8)  # TODO
    if size != 0:
      hash_num = self.file.read_int()
