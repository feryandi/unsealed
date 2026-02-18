from pathlib import Path
from pprint import pprint
import re
from ...assets.actor import Actor, Action
from ...assets.resource import Resource, ResourceType
from ...utils.file import File


class SealActorDecoder:
  def __init__(self, path: Path):
    self.path = path
    try:
      with open(path, "rb") as dat:
        self.file = File(dat.read())
    except Exception:
      raise Exception("Unable to open actor file")
    self.actor = None

  def decode(self) -> Actor:
    _ukwn = self.file.read_int()  # TODO
    name = self.file.read_string(self.file.read_int())
    filename = self.file.read_string(self.file.read_int())

    if filename is not None:
      if name is None:
        name = filename
      self.actor = Actor(name, filename)

    if self.actor is None:
      raise Exception("Actor was not initialized properly")

    action_num = self.file.read_int()

    for i in range(action_num):
      # 0: Common
      # 11: Example: T_Pu1.act, N_boyA.act, N_adelA.act, T_Ni2.act
      _x = self.file.read_int()  # TODO
      __arr_z = []
      for i in range(8):
        __arr_z.append(self.file.read_int())  # TODO

      name = self.file.read_string(self.file.read_int())
      filename = self.file.read_string(self.file.read_int())

      if filename is not None:
        if name is None:
          name = filename
        action = Action(name, filename)
        self.actor.actions.append(action)
      else:
        print("Warning: Action filename is empty")

      if action is not None:
        resource_num = self.file.read_int()
        _pad = self.file.read_int()  # TODO
        for m in range(resource_num):
          resource = self.__decode_effect()
          if resource is not None:
            action.resources.append(resource)

    __arr_z = []
    for i in range(8):
      __arr_z.append(self.file.read_int())  # TODO
    return self.actor

  def __decode_effect(self) -> Resource:
    _x = self.file.read_int()  # TODO

    __arr_z = []
    for i in range(8):
      __arr_z.append(self.file.read_int())  # TODO

    name = self.file.read_string(self.file.read_int())
    filename = self.file.read_string(self.file.read_int())
    resource = Resource(name, filename)

    _x = self.file.read_int()
    resource.index = self.file.read_int()  # Frame index
    resource.type = ResourceType(self.file.read_short())
    _x = self.file.read(20)

    return resource
