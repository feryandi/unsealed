"""Shared package resources (the application icon, …).

Lives at the top of the `unsealed` package so BOTH the reader and the
viewer can reach it without violating the one-directional import rule
(neither subpackage imports the other; both may import `unsealed.*`).
"""

from __future__ import annotations

import sys
from pathlib import Path

ICON_NAME = "icon.ico"
LOGO_NAME = "logo.png"
APP_USER_MODEL_ID = "Unsealed.Reader"


def set_app_user_model_id(app_id: str = APP_USER_MODEL_ID) -> None:
  """Give this process its own Windows taskbar id (no-op elsewhere).

  Running via `python -m ...` makes the OS process `python.exe`, so
  Windows groups the taskbar button under Python and shows Python's
  icon even after `setWindowIcon`. Assigning an explicit AppUserModelID
  before any window is created detaches the button so it uses our own
  window icon. Best-effort — must never stop the app from launching.
  """
  if sys.platform != "win32":
    return
  try:
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
  except Exception:
    pass


def icon_path() -> Path:
  """Absolute path to the bundled application icon (`.ico`).

  Resolves from source AND from a PyInstaller bundle: the `.spec` files
  ship the icon at `unsealed/icon.ico`, which PyInstaller extracts under
  `sys._MEIPASS` (onefile) / `_internal` (onedir). Falls back to the
  file next to this module when running from source.
  """
  return _resource_path(ICON_NAME)


def logo_path() -> Path:
  """Absolute path to the bundled logo image (`.png`)."""
  return _resource_path(LOGO_NAME)


def _resource_path(name: str) -> Path:
  """Resolve a bundled data file both from source and PyInstaller."""
  base = getattr(sys, "_MEIPASS", None)
  if base is not None:
    bundled = Path(base) / "unsealed" / name
    if bundled.exists():
      return bundled
  return Path(__file__).resolve().parent / name
