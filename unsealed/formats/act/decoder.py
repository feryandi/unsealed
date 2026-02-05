from assets.actor import Actor
from assets.action import Action
from assets.resource import Resource
from utils.file import File


class SealActorDecoder:
  def __init__(self, path):
    self.path = path
    self.file = None
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open actor file")
    self.actor = None

  def decode(self):
    if self.file is None:
      raise Exception("File was not initialized properly")
    try:
      ukwn = self.file.read_int()  # TODO
      # print(ukwn)
      name = self.__read_string()
      filename = self.__read_string()

      if filename is not None:
        if name is None:
          name = filename
        self.actor = Actor(name, filename)

      if self.actor is None:
        raise Exception("Actor was not initialized properly")

      action_num = self.file.read_int()

      for i in range(action_num):
        x = self.file.read_int()  # TODO
        pad = self.file.read(32)  # TODO
        name = self.__read_string()
        filename = self.__read_string()

        if filename is not None:
          if name is None:
            name = filename
          action = Action(name, filename)
          self.actor.add_action(action)
        else:
          print("Warning: Action filename is empty")

        if action is not None:
          resource_num = self.file.read_int()
          pad = self.file.read(4)  # TODO
          for m in range(resource_num):
            resource = self.__decode_effect()
            if resource is not None:
              action.add_resource(resource)

      pad = self.file.read(36)  # TODO
      return self.actor
    except Exception as e:
      raise e

  def __decode_effect(self):
    assert self.file is not None, "File was not initialized properly"
    x = self.file.read_int()  # TODO
    for i in range(8):
      z = self.file.read_int()  # TODO
    name = self.__read_string()
    filename = self.__read_string()
    _ = self.file.read(8)
    resource_type = self.file.read_int()
    # 1: effect
    # 5: sound
    _ = self.file.read(18)
    return Resource(name, filename)

  def __read_string(self) -> str | None:
    assert self.file is not None, "File was not initialized properly"
    str_len = self.file.read_int()
    if str_len == 0:
      return None
    return self.file.read_string(str_len)
