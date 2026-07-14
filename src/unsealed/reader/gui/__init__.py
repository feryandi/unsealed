"""PySide6 desktop GUI for the Unsealed reader (opt-in `gui` extra).

The GUI is *dynamically* linked against PySide6 (LGPLv3): PySide6 is an
opt-in dependency and must never be statically bundled, so distributing
the reader binary stays LGPL-compliant. Consequently PySide6 is imported
lazily here — importing `unsealed.reader.gui` never drags in Qt, which
keeps the headless reader (and its PyInstaller exe) free of Qt.
"""

from pathlib import Path


def run_gui(output_dir: Path | None = None) -> int:
  """Launch the desktop GUI. Returns a process exit code.

  Imports Qt lazily and prints an install hint if the `gui` extra is
  not installed, so the headless entry point degrades gracefully.
  """
  try:
    from .app import launch
  except ImportError:
    import sys

    if getattr(sys, "frozen", False):
      # A frozen build can't pip-install; the GUI ships as its own zip.
      print("This build has no GUI. Use the separate 'unsealed-reader-gui'")
      print("download, or run a 'decode' command here.")
    else:
      print("The GUI requires PySide6. Install it with:")
      print('  pip install -e ".[gui]"')
    return 1
  return launch(output_dir)
