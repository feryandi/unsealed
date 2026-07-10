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

    # Private-server key recovery (set when a .spak needs an unknown key).
    needs_key: bool = False
    install_dir: Optional[str] = None  # game dir to recover the key from
    recover_busy: bool = False  # a recovery attempt is in flight
    recover_status: Optional[str] = None  # progress text while busy
    alert: Optional[str] = None  # e.g. "admin required", failures
