from pathlib import Path

from ..assets.blob import Blob
from ..formats.edt.format import SealEdtFormat
from ..formats.blob.format import BlobFormat


class EdtPipeline:
  """Decode a `.edt` and write plaintext as `decoded_<name>.edt`."""

  def run(self, filepath: Path, output_dir: Path) -> None:
    if not filepath.is_file():
      raise Exception(f"File not found: {filepath}")

    edt_format = SealEdtFormat()
    edt = edt_format.decode(filepath)

    blob = Blob()
    blob.value = edt.value
    blob.name = f"decoded_{edt.name}"
    blob.extension = "edt"

    BlobFormat().encode(blob, output_dir)
