"""Vendored third-party executables and how to locate them.

Currently just ``bkcrack`` (see ``bkcrack/PROVENANCE.md``): a prebuilt
binary per OS/arch lets the known-plaintext ``.spak`` key recovery work
cross-platform without a memory dump. The binaries are NOT committed --
``fetch.py`` downloads the pinned, checksum-verified build into
``bkcrack/`` at build time. ``bkcrack_path()`` returns the executable
matching the host, resolved both from source and from a PyInstaller
bundle. Stdlib-only so it stays importable from the Qt-free ``decode``
path.
"""

from __future__ import annotations

import os
import platform
import stat
import sys
from pathlib import Path


class BkcrackUnavailable(RuntimeError):
  """No bundled bkcrack binary exists for the host platform."""


def host_asset_name() -> str:
  """Filename of the bkcrack build for this OS/arch (see PROVENANCE).

  Shared with ``fetch.py`` so the downloaded name and the looked-up name
  can never drift apart.
  """
  system = platform.system()
  machine = platform.machine().lower()
  if system == "Windows":
    # Only the x64 build is shipped; Windows-on-ARM runs it emulated.
    return "bkcrack-windows-x86_64.exe"
  if system == "Darwin":
    arch = "arm64" if machine in ("arm64", "aarch64") else "x86_64"
    return f"bkcrack-macos-{arch}"
  if system == "Linux":
    arch = "aarch64" if machine in ("aarch64", "arm64") else "x86_64"
    return f"bkcrack-linux-{arch}"
  raise BkcrackUnavailable(f"unsupported platform: {system} {machine}")


def _vendor_dir() -> Path:
  """The ``bkcrack/`` data dir, from source or a PyInstaller bundle."""
  base = getattr(sys, "_MEIPASS", None)
  if base is not None:
    bundled = Path(base) / "unsealed" / "reader" / "vendor" / "bkcrack"
    if bundled.exists():
      return bundled
  return Path(__file__).resolve().parent / "bkcrack"


def _ensure_executable(path: Path) -> None:
  """Best-effort +x; wheels/PyInstaller can drop the exec bit."""
  try:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  except OSError:
    pass


def bkcrack_path() -> Path:
  """Absolute path to the runnable bkcrack for this host.

  Raises :class:`BkcrackUnavailable` if the platform is unsupported or
  the binary is missing from the install.
  """
  path = _vendor_dir() / host_asset_name()
  if not path.is_file():
    raise BkcrackUnavailable(
      f"bkcrack not found at {path}. Binaries are fetched, not committed: "
      "run 'python -m unsealed.reader.vendor.fetch' to download it."
    )
  if os.name != "nt":
    _ensure_executable(path)
  return path
