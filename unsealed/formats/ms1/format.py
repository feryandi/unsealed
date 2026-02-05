import re

from pathlib import Path
from typing import Pattern, Type

from formats.base import BaseFormat
from assets.model import Model
from formats.ms1.decoder import SealMeshDecoder
from formats.bn1.decoder import SealBoneDecoder
from formats.an1.decoder import SealAnimationDecoder


class SealMeshFormat(BaseFormat[Model]):
  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.ms1$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Model]:
    return Model

  def decoder(self, path: Path) -> Model:
    model = Model()

    geometry_decoder = SealMeshDecoder(path)
    geometry = geometry_decoder.decode()
    model.add_geometry(geometry)

    bone_path = path.with_suffix(".bn1")
    if bone_path.is_file():
      bone_decoder = SealBoneDecoder(bone_path)
      skeleton = bone_decoder.decode()
      model.add_skeleton(skeleton)

    animation_path = path.with_suffix(".an1")
    if animation_path.is_file():
      animation_decoder = SealAnimationDecoder(animation_path)
      animations = animation_decoder.decode()
      for animation in animations:
        model.add_animation("default", animation)

    return model

  def encoder(self, asset: Model, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
