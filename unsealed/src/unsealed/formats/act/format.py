import re

from pathlib import Path
from typing import Pattern, Type

from ...core.asset import Asset
from ..base import BaseFormat
from ...assets.model import Model
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

  def decoder(self, path: Path) -> Model:
    self.actor_decoder = SealActorDecoder(path)
    actor = self.actor_decoder.decode()

    mesh_file_path = path.with_name(actor.filename).with_suffix(".ms1")
    self.mesh_format = SealMeshFormat()
    model = self.mesh_format.decode(mesh_file_path)

    for action in actor.actions:
      animation_path = path.with_name(f"{action.filename}.an1")
      if animation_path.is_file():
        animation_decoder = SealAnimationDecoder(animation_path)
        self.action_decoders.append(animation_decoder)
        animations = animation_decoder.decode()
        for animation in animations:
          model.add_animation(action.name, animation)

    return model

  def encoder(self, asset: Model, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
