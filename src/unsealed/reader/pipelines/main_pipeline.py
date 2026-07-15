import re
from pathlib import Path
from typing import List, Tuple

from .actor_pipeline import ActorPipeline
from .dat_pipeline import DatPipeline
from .ed_pipeline import EdPipeline
from .edp_pipeline import EdpPipeline
from .edt_pipeline import EdtPipeline
from .map_pipeline import MapPipeline
from .mdt_pipeline import MdtPipeline
from .menu_pipeline import MenuPipeline
from .object_pipeline import ObjectPipeline
from .scr_pipeline import ScrPipeline
from .spak_pipeline import SpakPipeline
from .texture_pipeline import TexturePipeline
from .tsv_pipeline import TsvPipeline
from .xml_pipeline import XmlPipeline

SUPPORTED_FILE_TYPES = {
  ".act": {"name": "Actor File", "pipeline": ActorPipeline()},
  ".ms1": {"name": "Mesh File", "pipeline": ObjectPipeline()},
  ".map": {"name": "Map File", "pipeline": MapPipeline()},
  ".men": {"name": "Menu File", "pipeline": MenuPipeline()},
  ".tex": {"name": "Texture File", "pipeline": TexturePipeline()},
  ".spak": {"name": "Packed Archive", "pipeline": SpakPipeline()},
  ".mdt": {"name": "Model Data Archive", "pipeline": MdtPipeline()},
  ".edt": {"name": "Encoded Data File", "pipeline": EdtPipeline()},
  ".edp": {"name": "Item Package Archive", "pipeline": EdpPipeline()},
  ".dat": {"name": "Data File", "pipeline": DatPipeline()},
  ".scr": {"name": "Script File", "pipeline": ScrPipeline()},
  ".tsv": {"name": "Tab-Separated Table", "pipeline": TsvPipeline()},
  ".xml": {"name": "XML Data Table", "pipeline": XmlPipeline()},
}

# Suffixes that vary by a numeric band (e.g. .ed1 … .ed17) and so can't be
# enumerated as fixed keys; matched by pattern after the exact lookup.
PATTERN_FILE_TYPES = [
  (re.compile(r"\.ed\d+$", re.IGNORECASE), {"name": "Item DB File", "pipeline": EdPipeline()}),
]


class MainPipeline:
  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.exists():
      raise Exception(f"File not found: {filepath}")

    filetype = filepath.suffix
    setup = SUPPORTED_FILE_TYPES.get(filetype)
    if setup is None:
      setup = next(
        (info for pat, info in PATTERN_FILE_TYPES if pat.search(filepath.name)),
        None,
      )

    if setup is None:
      raise Exception(f"No pipeline available for file type: {filetype}")

    setup["pipeline"].run(filepath, output_dir)

  def get_supported_file_types(self) -> List[Tuple[str, str]]:
    fixed = [(filetype, info["name"]) for filetype, info in SUPPORTED_FILE_TYPES.items()]
    patterned = [(pat.pattern, info["name"]) for pat, info in PATTERN_FILE_TYPES]
    return fixed + patterned
