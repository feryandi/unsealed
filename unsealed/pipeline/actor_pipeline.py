from pathlib import Path

from formats.act.format import SealActorFormat
from formats.glb.format import GlbFormat
from pipeline.texture_pipeline import TexturePipeline


class ActorPipeline:
  def run(self, filepath: Path):
    if not filepath.exists():
      raise Exception(f"File not found: {filepath}")

    format = SealActorFormat()
    model = format.decode(filepath)

    texture_pipeline = TexturePipeline()
    if model.geometry is not None:
      for material in model.geometry.materials:
        if material.bitmap != "":
          texture_pipeline.run(filepath.with_name(material.bitmap), "png")
        for sub_material in material.sub_materials:
          if sub_material.bitmap != "":
            texture_pipeline.run(filepath.with_name(sub_material.bitmap), "png")

    gltf_format = GlbFormat()
    gltf_format.encode(model, Path(filepath))
    return
