"""Recent-files list, persisted via QSettings.

Kept format-agnostic: just an ordered, de-duplicated list of paths,
newest first, capped at MAX_RECENT. The welcome screen reads it; the
main window appends to it whenever a file is opened.
"""

from pathlib import Path

from PySide6.QtCore import QSettings

_KEY = "recentFiles"
MAX_RECENT = 10


def load() -> list[Path]:
  """Return recent paths, newest first (missing files filtered out)."""
  raw = QSettings().value(_KEY, [])
  if isinstance(raw, str):
    raw = [raw]
  return [Path(p) for p in (raw or []) if Path(p).is_file()]


def add(path: Path) -> None:
  """Record a freshly opened file at the top of the list."""
  entries = [str(p) for p in load()]
  target = str(Path(path))
  if target in entries:
    entries.remove(target)
  entries.insert(0, target)
  QSettings().setValue(_KEY, entries[:MAX_RECENT])
