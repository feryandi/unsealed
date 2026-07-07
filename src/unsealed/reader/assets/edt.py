from typing import Optional
from ..core.asset import Asset


class Edt(Asset):
  """Decoded contents of a Seal Online `.edt` file.

  `value` holds the *plaintext* bytes (after decryption). The same
  asset is fed back into `SealEdtFormat.encode` to produce the
  obfuscated `.edt` again.
  """

  def __init__(self) -> None:
    super().__init__()
    self.value: Optional[bytes] = None  # decoded (plaintext) bytes
    self.name: Optional[str] = None
    # Output extension detected from the decoded content (e.g. the file
    # may still be a proprietary Seal format): "scr" / "dat" / "bin".
    self.extension: str = "bin"

  def __repr__(self) -> str:
    size = len(self.value) if self.value is not None else 0
    return f"<Edt name:{self.name} ext:{self.extension} {size} bytes>"
