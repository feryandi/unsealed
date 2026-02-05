import re

from pathlib import Path
from typing import Pattern, Type

from core.asset import Asset
from formats.base import BaseFormat
from assets.model import Model
from formats.an1.decoder import SealAnimationDecoder
from formats.act.decoder import SealActorDecoder
from formats.ms1.format import SealMeshFormat


class SealActorFormat(BaseFormat):
  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.act$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Asset]:
    return Model

  def decoder(self, path: Path) -> Model:
    actor_decoder = SealActorDecoder(path)
    actor = actor_decoder.decode()

    mesh_file_path = path.with_name(actor.filename).with_suffix(".ms1")
    mesh_file_format = SealMeshFormat()
    model = mesh_file_format.decode(mesh_file_path)

    for action in actor.actions:
      animation_path = path.with_name(f"{action.filename}.an1")
      if animation_path.is_file():
        animation_decoder = SealAnimationDecoder(animation_path)
        animations = animation_decoder.decode()
        for animation in animations:
          model.add_animation(action.name, animation)

    return model

  def encoder(self, asset: Model, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
