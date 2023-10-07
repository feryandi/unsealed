from file import File
from animation.animation import Animation
from animation.keyframe import Keyframe


class SealActionFileDecoder:
  def __init__(self, path):
    self.path = path
    self.file = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except:
      raise Exception("Unable to open action file")
    self.animations = []

  def decode(self):
    # TODO: This doesn't work for: N_arus.act, T_by.act
    try:
      ukwn = self.file.read(4)  # TODO
      name = self.__read_string()
      filename = self.__read_string()
      self.animations.append({
        "name": name,
        "filename": filename
      })
      animation_num = self.file.read_int()

      for i in range(animation_num):
        pad = self.file.read(36)  # TODO
        name = self.__read_string()
        filename = self.__read_string()
        self.animations.append({
          "name": name,
          "filename": filename
        })

        animation_effect_num = self.file.read_int()
        pad = self.file.read(4)  # TODO
        for m in range(animation_effect_num):
          self.__decode_effect()  # TODO
      
      pad = self.file.read(36)  # TODO
      return self.animations
    except Exception as e:
      print(hex(self.file.pointer))
      raise e

  def __decode_effect(self):
    pad = self.file.read(36)
    name = self.__read_string()
    filename = self.__read_string()
    w = self.file.read(30)

  def __read_string(self):
    str_len = self.file.read_int()
    if str_len == 0:
      return None
    return self.file.read_string(str_len)
