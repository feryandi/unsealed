from pygltflib import GLTF2
from pygltflib.utils import ImageFormat, Image

from encoder.gltf import GLTF


class GLB:
  def __init__(self, model):
    self.model = model

  def encode(self, output_path: str):
    if self.model is None:
      raise Exception("Model is not defined for GLB encoding")

    gltf2_encoder = GLTF()
    gltf2_encoder.encode(self.model, output_path)

    gltf = GLTF2().load(output_path + ".gltf")
    # Convert to GLB (this automatically embeds textures and other resources)
    if gltf is not None:
      gltf.convert_images(ImageFormat.DATAURI)
      gltf.save_binary(output_path + ".glb")
    else:
      raise Exception("Failed to generate GLB file")
