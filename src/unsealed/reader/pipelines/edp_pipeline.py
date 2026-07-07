import json
from pathlib import Path

from ..formats.edp.format import SealEdpFormat


class EdpPipeline:
  """Decode a `.edp` item package (`item_pak.edp`) and write a JSON file
  listing every bundled member (`ITEM.ED1` .. `ITEM.EDT`) with its parsed
  item records."""

  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.is_file():
      raise Exception(f"File not found: {filepath}")

    archive = SealEdpFormat().decode(filepath)

    total = sum(m["count"] for m in archive.members)
    summary = {
      "source": archive.source_name,
      "members": len(archive.members),
      "total_items": total,
      "contents": archive.members,
    }
    out = output_dir / f"{filepath.name}.json"
    out.write_text(
      json.dumps(summary, indent=2, ensure_ascii=False, default=str),
      encoding="utf-8",
    )
    print(
      f"{filepath.name}: {len(archive.members)} member(s), {total} item(s) -> {out.name}"
    )
