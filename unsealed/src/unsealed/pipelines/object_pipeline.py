from pathlib import Path

from ..formats.ms1.format import SealMeshFormat
from ..formats.glb.format import GlbFormat
from .texture_pipeline import TexturePipeline


class ObjectPipeline:
  def run(self, filepath: Path, output_dir: Path):
    if not filepath.exists():
      raise Exception(f"File not found: {filepath}")

    format = SealMeshFormat()
    model = format.decode(filepath)

    texture_pipeline = TexturePipeline()
    if model.geometry is not None:
      for material in model.geometry.materials:
        if material.bitmap != "":
          texture_pipeline.run(filepath.with_name(material.bitmap), output_dir, "png")
        for sub_material in material.sub_materials:
          if sub_material.bitmap != "":
            texture_pipeline.run(
              filepath.with_name(sub_material.bitmap), output_dir, "png"
            )

    gltf_format = GlbFormat()
    gltf_format.encode(model, output_dir)
    return
