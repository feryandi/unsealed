import re

from pathlib import Path
from typing import Pattern, Type

from ..base import BaseFormat
from ...assets.model import Model
from ...vfs import Resource
from ..ms1.decoder import SealMeshDecoder
from ..bn1.decoder import SealBoneDecoder
from ..an1.decoder import SealAnimationDecoder
from ..sha.decoder import SealShaDecoder


class SealMeshFormat(BaseFormat[Model]):
  def __init__(self) -> None:
    self.geometry_decoder: object = None
    self.bone_decoder: object = None
    self.animation_decoder: object = None

  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.ms1$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Model]:
    return Model

  def decoder(self, res: Resource) -> Model:
    model = Model()
    model.name = res.stem

    self.geometry_decoder = SealMeshDecoder(res.open())
    geometry = self.geometry_decoder.decode()
    model.add_geometry(geometry)

    sha = res.with_suffix(".sha")
    if sha.exists():
      model.add_shaders(SealShaDecoder(sha.open()).decode())

    bone = res.with_suffix(".bn1")
    if bone.exists():
      self.bone_decoder = SealBoneDecoder(bone.open())
      skeleton = self.bone_decoder.decode()
      model.add_skeleton(skeleton)

    animation = res.with_suffix(".an1")
    if animation.exists():
      self.animation_decoder = SealAnimationDecoder(animation.open())
      animations = self.animation_decoder.decode()
      for anim in animations:
        model.add_animation("default", anim)

    return model

  def encoder(self, asset: Model, path: Path) -> None:
    raise NotImplementedError("Encoder is not implemented")
