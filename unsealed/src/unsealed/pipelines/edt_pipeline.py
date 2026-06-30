from pathlib import Path

from ..assets.blob import Blob
from ..formats.edt.format import SealEdtFormat
from ..formats.blob.format import BlobFormat


class EdtPipeline:
  """Decode a `.edt` and write the plaintext with a content-detected
  extension (`.scr` for ASCII scripts, `.dat` for Seal data files, else
  `.bin`) so the right downstream decoder can claim it."""

  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.is_file():
      raise Exception(f"File not found: {filepath}")

    edt_format = SealEdtFormat()
    edt = edt_format.decode(filepath)

    blob = Blob()
    blob.value = edt.value
    blob.name = edt.name
    blob.extension = edt.extension

    BlobFormat().encode(blob, output_dir)
