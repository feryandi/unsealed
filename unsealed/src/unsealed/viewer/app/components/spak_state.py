from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class SpakComponent:
    """State for the in-viewer .spak archive browser.

    When a .spak is opened the archive is extracted to `root` (a temp
    directory, layout preserved so sibling files resolve), and `entries`
    holds the viewable files relative to `root`. The browser window is
    shown while `active` is True.
    """

    active: bool = False
    archive_name: str = ""
    root: Optional[Path] = None
    entries: List[Path] = field(default_factory=list)
    filter_text: str = ""
    error: Optional[str] = None
