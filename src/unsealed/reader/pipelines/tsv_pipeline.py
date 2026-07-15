import json
from pathlib import Path

from ..formats.tsv.decoder import SealTsvDecoder
from ..formats.records import schema_for_filename
from ..vfs import Resource


class TsvPipeline:
  """Decode a `.tsv` (tab-delimited table) and write JSON. If a built-in
  schema matches the filename (e.g. guarder/polymorph), the rows are
  labelled into `records`; otherwise the raw `rows` are written."""

  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.is_file():
      raise Exception(f"File not found: {filepath}")

    schema = schema_for_filename("tsv", filepath.stem)
    tsv = SealTsvDecoder(Resource.for_disk_file(filepath).open()).decode(schema)
    tsv.name = filepath.stem

    if not tsv.is_table:
      summary = {
        "name": tsv.name,
        "type": "string_list",
        "count": len(tsv.strings),
        "strings": tsv.strings,
      }
      note = f"string list, {len(tsv.strings)} entries (not a table)"
    elif tsv.schema_name is not None:
      summary = {
        "name": tsv.name,
        "schema": tsv.schema_name,
        "count": len(tsv.records),
        "records": tsv.records,
      }
      note = f"schema={tsv.schema_name}, {len(tsv.records)} records"
    else:
      summary = {
        "name": tsv.name,
        "lines": len(tsv.lines),
        "rows": len(tsv.rows),
        "data": tsv.rows,
      }
      note = f"{len(tsv.lines)} lines, {len(tsv.rows)} rows (no schema)"

    out = output_dir / f"{filepath.stem}.tsv.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{filepath.name}: {note}")
