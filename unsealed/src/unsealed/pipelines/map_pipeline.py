from pathlib import Path

from ..formats.map.format import SealMapFormat
from ..formats.blob.format import BlobFormat
from ..formats.heightmap.format import HeightmapFormat
from ..formats.mdt.format import SealMdtFormat
from .object_pipeline import ObjectPipeline
from .texture_pipeline import TexturePipeline


class MapPipeline:
  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.exists():
      raise Exception(f"File not found: {filepath}")

    format = SealMapFormat()
    terrain = format.decode(filepath)

    heightmap_format = HeightmapFormat()
    heightmap_format.encode(terrain, filepath.with_suffix(".png"))

    mdt_format = SealMdtFormat()
    directory = mdt_format.decode(filepath.with_suffix(".mdt"))

    for file in directory.list:
      blob_format = BlobFormat()
      blob_format.encode(file, filepath.with_name(f"{file.filename}.{file.extension}"))

    tex_pipeline = TexturePipeline()
    tex_pipeline.run(filepath.with_suffix(".tex"), output_dir)

    object_pipeline = ObjectPipeline()
    for object in terrain.object_files:
      object_pipeline.run(filepath.with_name(object), output_dir)
