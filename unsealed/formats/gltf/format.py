import re
import json

from pathlib import Path
from typing import Pattern, Type

from formats.base import BaseFormat
from assets.model import Model
from formats.gltf.encoder import GltfEncoder


class GltfFormat(BaseFormat[Model]):
  @property
  def extensions(self) -> Pattern[str]:
    return re.compile(r"\.gltf$", re.IGNORECASE)

  @property
  def asset_type(self) -> Type[Model]:
    return Model

  def decoder(self, path: Path) -> Model:
    raise NotImplementedError("Decoder is not implemented")

  def encoder(self, asset: Model, path: Path) -> None:
    gltf2_encoder = GltfEncoder()
    gltf2 = gltf2_encoder.encode(asset, path)

    with open(path.with_suffix(".gltf"), "w") as f:
      f.write(json.dumps(gltf2, indent=2))
