import json
from pathlib import Path

from ..formats.xml.format import SealXmlFormat


class XmlPipeline:
  """Decode a Seal `.xml` data table (e.g. a decrypted `bpet*` table) and
  write JSON. The schema is embedded (the `<item>` attribute names), so the
  rows are labelled into `records` directly; a non-table document (no
  element children) is written as `strings`."""

  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.is_file():
      raise Exception(f"File not found: {filepath}")

    xml = SealXmlFormat().decode(filepath)

    if not xml.is_table:
      summary = {
        "name": xml.name,
        "type": "string_list",
        "count": len(xml.strings),
        "strings": xml.strings,
      }
      note = f"non-table XML, {len(xml.strings)} lines"
    else:
      summary = {
        "name": xml.name,
        "root": xml.root_tag,
        "columns": xml.columns,
        "count": len(xml.records),
        "records": xml.records,
      }
      note = f"<{xml.root_tag}>, {len(xml.records)} records × {len(xml.columns)} cols"

    out = output_dir / f"{filepath.stem}.xml.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{filepath.name}: {note}")
