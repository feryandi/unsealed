import json
from pathlib import Path

from ..formats.dat.format import SealDatFormat


class DatPipeline:
  """Decode a `.dat` and write a JSON summary (type, version, count, and
  any decoded elements). Until a body decoder is registered for the
  type+version, `elements` is empty and only the header is written."""

  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.is_file():
      raise Exception(f"File not found: {filepath}")

    dat = SealDatFormat().decode(filepath)

    summary = {
      "type": dat.type_name,
      "version": dat.version,
      "count": dat.count,
      "decoded": len(dat.elements),
      "elements": dat.elements,
    }
    out = output_dir / f"{filepath.stem}.dat.json"
    out.write_text(
      json.dumps(summary, indent=2, ensure_ascii=False, default=str),
      encoding="utf-8",
    )
    print(f"{filepath.name}: {dat.type_name} v{dat.version}, {dat.count} element(s)")
