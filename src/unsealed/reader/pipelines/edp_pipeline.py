from pathlib import Path
from typing import List

from ..formats.edp.format import SealEdpFormat


class EdpPipeline:
  """Unpacks a Seal Online `.edp` (EDT package), then runs the matching
  pipeline on each extracted member.

  Members come out still `.edt`-encrypted (an `.edp` is a bundle of
  `.edt` files — see `formats/edp/decoder.py`), so extracting them yields
  real, self-contained `ITEM.ED1` / `ITEM.EDT` files; dispatching each
  one back through the reader then decrypts and parses it exactly as a
  loose shard on disk would be.
  """

  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.exists():
      raise Exception(f"File not found: {filepath}")

    directory = SealEdpFormat().decode(filepath)

    extract_dir = output_dir / filepath.stem
    extract_dir.mkdir(parents=True, exist_ok=True)

    extracted: List[Path] = []
    for blob in directory.list:
      if blob.value is None or blob.name is None:
        continue
      rel = blob.name + (f".{blob.extension}" if blob.extension else "")
      dest = extract_dir / rel
      with open(dest, "wb") as f:
        f.write(blob.value)
      extracted.append(dest)
      print(f"Extracted {rel}")

    # Imported lazily: main_pipeline registers EdpPipeline. Dispatching
    # through MainPipeline (rather than SUPPORTED_FILE_TYPES directly, as
    # MdtPipeline does) is what gets the `.ed<n>` band suffixes matched —
    # they live in PATTERN_FILE_TYPES, not the fixed table.
    from .main_pipeline import MainPipeline

    main = MainPipeline()
    self._decode(main, extracted, extract_dir)

    # An `.edt` member only decrypts to its payload (ITEM.EDT -> the
    # ItemFile ITEM.dat), so decode that second layer too — otherwise the
    # one headered member is the only one left unparsed.
    produced = [
      p
      for p in sorted(extract_dir.iterdir())
      if p.is_file() and p not in extracted and p.suffix.lower() != ".json"
    ]
    self._decode(main, produced, extract_dir)

  @staticmethod
  def _decode(main, paths: List[Path], output_dir: Path) -> None:
    for path in paths:
      try:
        main.run(path, output_dir)
      except Exception as e:
        print(f"Warning: failed to process {path.name}: {e}")
