from pathlib import Path
from typing import Any, Dict, Optional

from ...assets.actor import Actor, Action
from ...assets.resource import Resource, ResourceType
from ...utils.file import File


class SealActorDecoder:
  def __init__(self, path: Path) -> None:
    self.path: Path = path
    self.unknown: Dict[str, Any] = {}
    try:
      with open(path, "rb") as dat:
        self.file: File = File(dat.read())
    except Exception:
      raise Exception("Unable to open actor file")
    self.actor: Optional[Actor] = None

  def decode(self) -> Actor:
    self.unknown["header_ukwn"] = self.file.read_int()
    name = self.file.read_string(self.file.read_int())
    filename = self.file.read_string(self.file.read_int())

    if filename is not None:
      if name is None:
        name = filename
      self.actor = Actor(name, filename)

    if self.actor is None:
      raise Exception("Actor was not initialized properly")

    action_num = self.file.read_int()

    for action_idx in range(action_num):
      # 0: Common
      # 11: Example: T_Pu1.act, N_boyA.act, N_adelA.act, T_Ni2.act
      self.unknown[f"action_{action_idx}_x"] = self.file.read_int()
      self.unknown[f"action_{action_idx}_arr"] = [
        self.file.read_int() for _ in range(8)
      ]

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
        self.unknown[f"action_{action_idx}_pad"] = self.file.read_int()
        for resource_idx in range(resource_num):
          resource = self.__decode_effect(action_idx, resource_idx)
          if resource is not None:
            action.resources.append(resource)

    self.unknown["tail_arr"] = [self.file.read_int() for _ in range(8)]
    return self.actor

  def __decode_effect(self, action_idx: int, resource_idx: int) -> Resource:
    prefix = f"action_{action_idx}_effect_{resource_idx}"
    self.unknown[f"{prefix}_x"] = self.file.read_int()
    self.unknown[f"{prefix}_arr"] = [self.file.read_int() for _ in range(8)]

    name = self.file.read_string(self.file.read_int())
    filename = self.file.read_string(self.file.read_int())
    resource = Resource(name, filename)

    self.unknown[f"{prefix}_x2"] = self.file.read_int()
    resource.index = self.file.read_int()  # Frame index
    resource.type = ResourceType(self.file.read_short())
    self.unknown[f"{prefix}_tail"] = self.file.read(20)

    return resource
