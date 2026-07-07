import json
from pathlib import Path

from ..formats.ed.format import SealItemDbFormat


class EdPipeline:
  """Decode an item-database shard (`.ed1`, `.ed2`, …) and write a JSON
  list of item records (id, name, stats, description)."""

  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.is_file():
      raise Exception(f"File not found: {filepath}")

    db = SealItemDbFormat().decode(filepath)

    summary = {
      "source": db.source_name,
      "format": db.format,
      "count": len(db.items),
      "items": db.items,
    }
    # Use the full name (item.ed1, item.ed2, …) so shards don't collide
    # on the shared "item" stem.
    out = output_dir / f"{filepath.name}.json"
    out.write_text(
      json.dumps(summary, indent=2, ensure_ascii=False, default=str),
      encoding="utf-8",
    )
    print(f"{filepath.name}: {db.format}, {len(db.items)} item(s)")
