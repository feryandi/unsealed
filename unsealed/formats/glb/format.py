import re

from pathlib import Path
from typing import Pattern, Type

from formats.base import BaseFormat
from formats.gltf.format import GltfFormat
from assets.model import Model
from pygltflib import GLTF2
from pygltflib.utils import ImageFormat


class GlbFormat(BaseFormat[Model]):
  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.glb$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Model]:
    return Model

  def decoder(self, path: Path) -> Model:
    raise NotImplementedError("Decoder is not implemented")

  def encoder(self, asset: Model, path: Path) -> None:
    gltf2_format = GltfFormat()
    gltf2_format.encode(asset, path.with_suffix(".gltf"))

    gltf = GLTF2().load(path.with_suffix(".gltf"))
    if gltf is not None:
      gltf.convert_images(ImageFormat.DATAURI, path.parent)
      gltf.save_binary(path.with_suffix(".glb"))
    else:
      raise Exception("Failed to generate GLB file")
