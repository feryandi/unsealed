from pathlib import Path

from pipeline.actor_pipeline import ActorPipeline
from pipeline.map_pipeline import MapPipeline
from pipeline.menu_pipeline import MenuPipeline
from pipeline.object_pipeline import ObjectPipeline
from pipeline.texture_pipeline import TexturePipeline

SUPPORTED_FILE_TYPES = {
  ".act": {"name": "Actor File", "pipeline": ActorPipeline()},
  ".ms1": {"name": "Mesh File", "pipeline": ObjectPipeline()},
  ".map": {"name": "Map File", "pipeline": MapPipeline()},
  ".men": {"name": "Menu File", "pipeline": MenuPipeline()},
  ".tex": {"name": "Texture File", "pipeline": TexturePipeline()},
}


class MainPipeline:
  def run(self, filepath: Path):
    if not filepath.exists():
      raise Exception(f"File not found: {filepath}")

    filetype = filepath.suffix
    setup = SUPPORTED_FILE_TYPES.get(filetype, None)

    if setup is None:
      raise Exception(f"No pipeline available for file type: {filetype}")

    setup["pipeline"].run(filepath)

  def get_supported_file_types(self):
    list = []
    for filetype, info in SUPPORTED_FILE_TYPES.items():
      list.append((filetype, info["name"]))
    return list
