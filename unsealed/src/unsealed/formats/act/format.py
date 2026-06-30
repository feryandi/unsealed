import re

from pathlib import Path
from typing import Pattern, Type

from ...core.asset import Asset
from ..base import BaseFormat
from ...assets.model import Model
from ...vfs import Resource
from ..an1.decoder import SealAnimationDecoder
from ..act.decoder import SealActorDecoder
from ..ms1.format import SealMeshFormat


class SealActorFormat(BaseFormat[Model]):
  def __init__(self) -> None:
    self.actor_decoder: object = None
    self.mesh_format: object = None
    self.action_decoders: list = []

  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.act$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Asset]:
    return Model

  def decoder(self, res: Resource) -> Model:
    self.actor_decoder = SealActorDecoder(res)
    actor = self.actor_decoder.decode()

    mesh_res = res.with_name(actor.filename).with_suffix(".ms1")
    self.mesh_format = SealMeshFormat()
    model = self.mesh_format.decode(mesh_res)

    for action in actor.actions:
      animation_res = res.with_name(f"{action.filename}.an1")
      if animation_res.exists():
        animation_decoder = SealAnimationDecoder(animation_res)
        self.action_decoders.append(animation_decoder)
        animations = animation_decoder.decode()
        for animation in animations:
          model.add_animation(action.name, animation)

    return model

  def encoder(self, asset: Model, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
