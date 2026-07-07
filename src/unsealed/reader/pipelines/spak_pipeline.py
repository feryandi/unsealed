from pathlib import Path
from typing import List

from ..formats.spak.format import SealSpakFormat


class SpakPipeline:
  """Unpacks a Seal Online .spak archive, then runs the matching
  pipeline on each contained file that has one (.ms1, .act, .map, ...).

  A .spak can hold arbitrary formats, including helper files (.an1/.bn1)
  consumed alongside a sibling; extracting the whole archive into one
  directory keeps those co-located so downstream pipelines find them.
  """

  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.exists():
      raise Exception(f"File not found: {filepath}")

    spak_format = SealSpakFormat()
    directory = spak_format.decode(filepath)

    extract_dir = output_dir / filepath.stem
    extract_dir.mkdir(parents=True, exist_ok=True)

    extracted: List[Path] = []
    for blob in directory.list:
      if blob.value is None or blob.name is None:
        continue
      rel = blob.name + (f".{blob.extension}" if blob.extension else "")
      dest = extract_dir / rel
      dest.parent.mkdir(parents=True, exist_ok=True)
      with open(dest, "wb") as f:
        f.write(blob.value)
      extracted.append(dest)
      print(f"Extracted {rel}")

    # Dispatch decodable members to their pipelines. Imported lazily to
    # avoid a circular import (main_pipeline registers SpakPipeline).
    from .main_pipeline import SUPPORTED_FILE_TYPES

    for path in extracted:
      setup = SUPPORTED_FILE_TYPES.get(path.suffix.lower())
      if setup is None or isinstance(setup["pipeline"], SpakPipeline):
        continue
      try:
        setup["pipeline"].run(path, output_dir)
      except Exception as e:
        print(f"Warning: failed to process {path.name}: {e}")
