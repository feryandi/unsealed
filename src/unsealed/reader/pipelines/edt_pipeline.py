import re
from pathlib import Path

from ..assets.blob import Blob
from ..formats.blob.format import BlobFormat
from ..formats.dat.decoder import SealDatDecoder
from ..formats.edt.band import band_layout, decode_item_band
from ..formats.edt.format import SealEdtFormat
from ..utils.file import File
from ..vfs import Resource
from .dat_pipeline import is_scr_type, render_scr

# Item-db shards (`.ed1` … `.ed17`): the same `.edt` cipher, but the
# plaintext is a headerless ItemFile band rather than a self-describing
# payload, so it is parsed here instead of being written out raw.
_BAND = re.compile(r"\.ed(?P<num>\d+)$", re.IGNORECASE)


class EdtPipeline:
  """Decode a `.edt` (or an `.ed<n>` item-db shard).

  A plain `.edt` classified as a Seal `.dat` (see `formats/edt/classify.py`)
  is decoded the rest of the way, same as `DatPipeline`: a type in
  `dat_pipeline.is_scr_type` (Monster/Item/QuestFile/Seller/the generic
  "Seal Online Data" family) is written as pipe-delimited `.scr` text;
  anything else falls back to its plaintext with a content-detected
  extension (`.xml`/`.tsv`/`.scr`/`.bin`) so the right downstream decoder
  can claim it. An `.ed<n>` band has no self-describing header to
  classify -- it is always the ItemFile layout (see `formats/edt/band.py`)
  -- so it is always written as `.scr`, named `<stem><n>.scr` (e.g.
  `item.ed32` -> `item32.scr`) so the shards don't collide on their shared
  stem.
  """

  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.is_file():
      raise Exception(f"File not found: {filepath}")

    edt = SealEdtFormat().decode(filepath)

    band = _BAND.search(filepath.name)
    if band:
      self._write_band(edt.value or b"", filepath, output_dir, band.group("num"))
      return

    if edt.extension == "dat":
      dat = SealDatDecoder(File(edt.value or b"", filepath.name)).decode()
      if is_scr_type(dat.type_name):
        out = output_dir / f"{filepath.stem}.scr"
        out.write_text(render_scr(dat), encoding="utf-8")
        print(
          f"{filepath.name}: {dat.type_name} v{dat.version}, "
          f"{len(dat.elements)} element(s) -> .scr"
        )
        return

    blob = Blob()
    blob.value = edt.value
    blob.name = edt.name
    blob.extension = edt.extension
    BlobFormat().encode(blob, output_dir)

  def _write_band(
    self, plain: bytes, filepath: Path, output_dir: Path, num: str
  ) -> None:
    # The companion `<stem>.edt` master names the band's layout; beside a
    # loose shard on disk that's `item.edt` next to `item.ed1`.
    res = Resource.for_disk_file(filepath)
    dat = decode_item_band(plain, filepath.name, band_layout(res))
    layout = "item-db" if dat.version else "legacy"
    out = output_dir / f"{filepath.stem}{num}.scr"
    out.write_text(render_scr(dat), encoding="utf-8")
    print(f"{filepath.name}: {layout}, {len(dat.elements)} item(s) -> {out.name}")
