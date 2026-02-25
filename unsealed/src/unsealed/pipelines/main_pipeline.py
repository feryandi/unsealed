from pathlib import Path
from typing import List, Tuple

from .actor_pipeline import ActorPipeline
from .map_pipeline import MapPipeline
from .menu_pipeline import MenuPipeline
from .object_pipeline import ObjectPipeline
from .texture_pipeline import TexturePipeline

SUPPORTED_FILE_TYPES = {
  ".act": {"name": "Actor File", "pipeline": ActorPipeline()},
  ".ms1": {"name": "Mesh File", "pipeline": ObjectPipeline()},
  ".map": {"name": "Map File", "pipeline": MapPipeline()},
  ".men": {"name": "Menu File", "pipeline": MenuPipeline()},
  ".tex": {"name": "Texture File", "pipeline": TexturePipeline()},
}


class MainPipeline:
  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.exists():
      raise Exception(f"File not found: {filepath}")

    filetype = filepath.suffix
    setup = SUPPORTED_FILE_TYPES.get(filetype, None)

    if setup is None:
      raise Exception(f"No pipeline available for file type: {filetype}")

    setup["pipeline"].run(filepath, output_dir)

  def get_supported_file_types(self) -> List[Tuple[str, str]]:
    list: List[Tuple[str, str]] = []
    for filetype, info in SUPPORTED_FILE_TYPES.items():
      list.append((filetype, info["name"]))
    return list
