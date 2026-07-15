import json
import re
from pathlib import Path

from ..assets.blob import Blob
from ..formats.blob.format import BlobFormat
from ..formats.edt.band import band_layout, decode_item_band
from ..formats.edt.format import SealEdtFormat
from ..vfs import Resource

# Item-db shards (`.ed1` … `.ed17`): the same `.edt` cipher, but the
# plaintext is a headerless ItemFile band rather than a self-describing
# payload, so it is parsed here instead of being written out raw.
_BAND = re.compile(r"\.ed\d+$", re.IGNORECASE)


class EdtPipeline:
  """Decode a `.edt` (or an `.ed<n>` item-db shard).

  A plain `.edt` is written back out as its plaintext with a
  content-detected extension (`.scr` for ASCII scripts, `.dat` for Seal
  data files, else `.bin`) so the right downstream decoder can claim it.
  An `.ed<n>` band has no self-describing header to classify, so it is
  parsed into item records and written as JSON.
  """

  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.is_file():
      raise Exception(f"File not found: {filepath}")

    edt = SealEdtFormat().decode(filepath)

    if _BAND.search(filepath.name):
      self._write_band(edt.value or b"", filepath, output_dir)
      return

    blob = Blob()
    blob.value = edt.value
    blob.name = edt.name
    blob.extension = edt.extension
    BlobFormat().encode(blob, output_dir)

  def _write_band(self, plain: bytes, filepath: Path, output_dir: Path) -> None:
    # The companion `<stem>.edt` master names the band's layout; beside a
    # loose shard on disk that's `item.edt` next to `item.ed1`.
    res = Resource.for_disk_file(filepath)
    dat = decode_item_band(plain, filepath.name, band_layout(res))
    layout = "item-db" if dat.version else "legacy"
    summary = {
      "source": filepath.name,
      "type": dat.type_name,
      "version": dat.version,
      "format": layout,
      "count": dat.count,
      "items": dat.elements,
    }
    # Keyed on the full name (item.ed1, item.ed2, …) so the shards don't
    # collide on their shared "item" stem.
    out = output_dir / f"{filepath.name}.json"
    out.write_text(
      json.dumps(summary, indent=2, ensure_ascii=False, default=str),
      encoding="utf-8",
    )
    print(f"{filepath.name}: {layout}, {dat.count} item(s)")
