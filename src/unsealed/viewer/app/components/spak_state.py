from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import List, Optional


@dataclass
class SpakComponent:
  """State for the in-viewer .spak archive browser.

  When a .spak is opened it is mounted (its directory read, nothing
  decrypted); `entries` holds the viewable file names inside it. Opening
  an entry decrypts just that file (and its deps) on demand. The browser
  window is shown while `active` is True.
  """

  active: bool = False
  archive_name: str = ""
  entries: List[PurePosixPath] = field(default_factory=list)
  filter_text: str = ""
  error: Optional[str] = None

  # Private-server key recovery. Mounting a fixed-password archive cracks
  # its key automatically (bundled bkcrack); `progress` (0..1) and
  # `recover_status` drive a determinate bar during that ~10s attack.
  # `needs_key` is set only when the crack can't recover the key.
  needs_key: bool = False
  recover_status: Optional[str] = None  # live phase label while cracking
  progress: Optional[float] = None  # crack completion 0..1, else None
