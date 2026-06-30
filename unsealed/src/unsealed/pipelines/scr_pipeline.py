import json
from pathlib import Path

from ..formats.scr.decoder import SealScrDecoder
from ..formats.scr.schema import schema_for_filename


class ScrPipeline:
  """Decode a `.scr` and write JSON. If a built-in schema matches the
  filename (e.g. drop*/npc*), the rows are labelled into `records`;
  otherwise the raw pipe-delimited `rows` are written."""

  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.is_file():
      raise Exception(f"File not found: {filepath}")

    schema = schema_for_filename(filepath.stem)
    scr = SealScrDecoder(filepath).decode(schema)
    scr.name = filepath.stem

    if scr.schema_name is not None:
      summary = {
        "name": scr.name,
        "schema": scr.schema_name,
        "headers": scr.header_values,
        "count": len(scr.records),
        "records": scr.records,
      }
      note = f"schema={scr.schema_name}, {len(scr.records)} records"
    else:
      summary = {
        "name": scr.name,
        "lines": len(scr.lines),
        "rows": len(scr.rows),
        "data": scr.rows,
      }
      note = f"{len(scr.lines)} lines, {len(scr.rows)} rows (no schema)"

    out = output_dir / f"{filepath.stem}.scr.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{filepath.name}: {note}")
