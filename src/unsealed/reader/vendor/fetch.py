"""Fetch the vendored bkcrack executable(s) at build time.

The binaries are intentionally NOT committed to git (see .gitignore).
This downloads the pinned, checksum-verified upstream release into
``vendor/bkcrack/`` so PyInstaller can bundle the host build. It is the
single source of truth for the bkcrack version and per-file checksums.

Run before packaging (needs the package importable, e.g. after
``pip install -e .``):

    python -m unsealed.reader.vendor.fetch          # just this host
    python -m unsealed.reader.vendor.fetch --all    # every platform

bkcrack is zlib-licensed; the notice ships in ``bkcrack/LICENSE.txt``.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import stat
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

from . import host_asset_name

BKCRACK_VERSION = "1.8.1"
_BASE = f"https://github.com/kimci86/bkcrack/releases/download/v{BKCRACK_VERSION}/"

# Output name -> (release asset, member name, extracted-binary sha256).
# Single source of truth for provenance; bump all three per version
# (see bkcrack/PROVENANCE.md).
_ASSETS: dict[str, Tuple[str, str, str]] = {
  "bkcrack-windows-x86_64.exe": (
    "bkcrack-1.8.1-win64.zip",
    "bkcrack.exe",
    "d3de2e1494c8db2a1550794cae4923956d76da9314e68198096f4b03f7f310d5",
  ),
  "bkcrack-macos-arm64": (
    "bkcrack-1.8.1-macOS-arm64.tar.gz",
    "bkcrack",
    "d9df5df27b8d9a8de839c9c838df984f7eae7c9cf61dfd18be2f1a80b93cdaf0",
  ),
  "bkcrack-macos-x86_64": (
    "bkcrack-1.8.1-macOS-x86_64.tar.gz",
    "bkcrack",
    "4309e56a7ae33f44243f23af7ec6b8c1a4389088f203378d1e410faeb8024942",
  ),
  "bkcrack-linux-x86_64": (
    "bkcrack-1.8.1-Linux-x86_64.tar.gz",
    "bkcrack",
    "116e51c44aac030858a344fb743f0f3de19b615823f2945874a560dcf0a048d4",
  ),
  "bkcrack-linux-aarch64": (
    "bkcrack-1.8.1-Linux-aarch64.tar.gz",
    "bkcrack",
    "7701d31d9316586fe12c385a894b366fae8da2a71eb13e24e40b77e9f987be96",
  ),
}


def vendor_dir() -> Path:
  """The ``vendor/bkcrack`` dir this module downloads into."""
  return Path(__file__).resolve().parent / "bkcrack"


def _download(url: str) -> bytes:
  req = urllib.request.Request(url, headers={"User-Agent": "unsealed"})
  with urllib.request.urlopen(req, timeout=120) as r:
    return r.read()


def _extract(blob: bytes, asset: str, member: str) -> bytes:
  """Pull the ``member`` binary out of a .zip or .tar.gz asset."""
  if asset.endswith(".zip"):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
      for n in z.namelist():
        if n.rsplit("/", 1)[-1] == member:
          return z.read(n)
  else:
    with tarfile.open(fileobj=io.BytesIO(blob)) as t:
      for m in t.getmembers():
        if m.isfile() and m.name.rsplit("/", 1)[-1] == member:
          return t.extractfile(m).read()
  raise RuntimeError(f"{member!r} not found in {asset!r}")


def _sha256(data: bytes) -> str:
  return hashlib.sha256(data).hexdigest()


def fetch_one(outname: str, dest: Optional[Path] = None, force: bool = False) -> Path:
  """Download + verify one bkcrack binary; returns its path.

  Idempotent: an existing file whose hash already matches is kept as-is.
  """
  if outname not in _ASSETS:
    raise KeyError(f"unknown bkcrack asset {outname!r}")
  asset, member, want = _ASSETS[outname]
  dest = dest or vendor_dir()
  dest.mkdir(parents=True, exist_ok=True)
  out = dest / outname
  if out.is_file() and not force and _sha256(out.read_bytes()) == want:
    return out
  data = _extract(_download(_BASE + asset), asset, member)
  got = _sha256(data)
  if got != want:
    raise RuntimeError(
      f"{outname}: sha256 mismatch (want {want}, got {got}); refusing to write"
    )
  out.write_bytes(data)
  if not outname.endswith(".exe"):
    out.chmod(out.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  return out


def fetch(
  dest: Optional[Path] = None, all_platforms: bool = False, force: bool = False
) -> List[Path]:
  """Fetch the host binary (default) or every platform's binary."""
  names = list(_ASSETS) if all_platforms else [host_asset_name()]
  return [fetch_one(n, dest, force) for n in names]


def main(argv=None) -> int:
  p = argparse.ArgumentParser(description="Download vendored bkcrack binaries.")
  p.add_argument(
    "--all",
    action="store_true",
    help="fetch every platform, not just this host",
  )
  p.add_argument("--force", action="store_true", help="re-download even if present")
  p.add_argument(
    "--dest", type=Path, default=None, help="output dir (default: vendor/bkcrack)"
  )
  args = p.parse_args(argv)
  try:
    paths = fetch(args.dest, all_platforms=args.all, force=args.force)
  except Exception as e:  # noqa: BLE001 - surface any fetch failure to the CLI
    print(f"error: {e}", file=sys.stderr)
    return 1
  for path in paths:
    print(f"ok  {path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
