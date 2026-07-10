"""Recover a private-server .spak ZipCrypto key from client memory.

Private servers repack archives with a fixed password + empty comment;
it can't be derived. The password is a plain constant that appears only
once the client's packed ``AutoUpdate.exe`` unpacks in memory.
Reusable pieces:

- ``scan_bytes`` / ``scan_dump`` -- find the key in a memory dump by
  testing candidate strings against a ``verify(key) -> bool`` (CRC
  check). An anchor-first pass (strings next to the client's
  ``CUR_VERSION`` config blob, where the key sits) is near-instant; a
  full string scan is the fallback. Pure Python, cross-platform.
- ``create_full_dump`` / ``find_pid`` / ``launch`` -- Windows helpers
  to snapshot a process (used by ``unsealed-reader recover-key``).
- ``find_dumps`` -- locate existing full dumps near an install (used by
  the reader's safe, scan-only auto-recovery).

Only the dump-*creation* helpers touch Windows APIs, and only when
called; scanning has no platform dependency.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Callable, Iterator, List, Optional

Verify = Callable[[bytes], bool]

# The key sits a few bytes before the client's version-config token.
_ANCHORS = (b"CUR_VERSION_EX", b"CUR_VERSION")


def _runs(data: bytes, lo: int, hi: int) -> Iterator[bytes]:
  for m in re.finditer(rb"[\x20-\x7e]{%d,%d}" % (lo, hi), data):
    yield m.group()
  for m in re.finditer(rb"(?:[\x20-\x7e]\x00){%d,%d}" % (lo, hi), data):
    yield m.group()[::2]


def _anchor_candidates(data: bytes, lo: int, hi: int) -> List[bytes]:
  """Distinct strings within +-96 bytes of a version-config anchor."""
  out: List[bytes] = []
  seen = set()
  for anchor in _ANCHORS:
    for enc in (anchor, anchor.decode().encode("utf-16le")):
      for m in re.finditer(re.escape(enc), data):
        window = data[max(0, m.start() - 96) : m.end() + 96]
        for cand in _runs(window, lo, hi):
          if cand not in seen:
            seen.add(cand)
            out.append(cand)
  return out


def scan_bytes(
  data: bytes, verify: Verify, lo: int = 6, hi: int = 64
) -> Optional[bytes]:
  """Return the first string in ``data`` that ``verify`` accepts."""
  for cand in _anchor_candidates(data, lo, hi):  # fast path
    if verify(cand):
      return cand
  seen = set()  # full scan
  for cand in _runs(data, lo, hi):
    if cand in seen:
      continue
    seen.add(cand)
    if verify(cand):
      return cand
  return None


def scan_dump(dump: Path, verify: Verify, lo: int = 6, hi: int = 64) -> Optional[bytes]:
  return scan_bytes(Path(dump).read_bytes(), verify, lo, hi)


def make_verifier(spak_path: Path) -> Verify:
  """A ``verify(key)`` that CRC-checks the smallest encrypted entry of a .spak."""
  import struct
  import zipfile
  import zlib

  from .zipcrypto import ZipDecryptor

  lh = struct.Struct("<IHHHHHIIIHH")
  zf = zipfile.ZipFile(spak_path, "r")
  infos = [i for i in zf.infolist() if not i.is_dir() and i.flag_bits & 0x1]
  if not infos:
    raise ValueError(f"{spak_path}: no encrypted entries to verify against")
  info = min(infos, key=lambda i: i.compress_size)
  with open(spak_path, "rb") as fp:
    fp.seek(info.header_offset)
    h = lh.unpack(fp.read(lh.size))
    fp.seek(info.header_offset + lh.size + h[9] + h[10])
    raw = fp.read(info.compress_size)
  crc = info.CRC
  deflated = info.compress_type == zipfile.ZIP_DEFLATED

  def verify(key: bytes) -> bool:
    try:
      body = ZipDecryptor(key).decrypt(raw)[12:]
      out = zlib.decompress(body, -15) if deflated else body
      return (zlib.crc32(out) & 0xFFFFFFFF) == crc
    except Exception:
      return False

  return verify


def find_dumps(install_dir: Path, min_size: int = 5 * 1024 * 1024) -> List[Path]:
  """Existing full memory dumps worth scanning (skip tiny minidumps).

  Looks in the install's ``Temp`` and the user %TEMP%, newest first.
  """
  seen: dict[Path, float] = {}
  temp = os.environ.get("TEMP") or os.environ.get("TMP")
  roots = [install_dir / "Temp"]
  if temp:
    roots.append(Path(temp))
  for root in roots:
    if not root.is_dir():
      continue
    for pat in ("*.dmp", "*.DMP", "AutoUpdate*"):
      for p in root.glob(pat):
        try:
          if p.is_file() and p.stat().st_size >= min_size:
            seen[p] = p.stat().st_mtime
        except OSError:
          pass
  return [p for p, _ in sorted(seen.items(), key=lambda kv: kv[1], reverse=True)]


def recover_from_existing_dumps(
  verify: Verify,
  install_dir: Path,
  on_status: Optional[Callable[[str], None]] = None,
) -> Optional[tuple[bytes, Path]]:
  """Scan existing full dumps near ``install_dir`` (non-interactive).

  CRC-gated by ``verify``, so a dump from another server simply yields
  nothing. ``on_status`` (if given) is called before each dump scan so a
  UI can show progress. Returns ``(key, dump_path)`` or ``None``.
  """
  for dump in find_dumps(install_dir):
    if on_status is not None:
      mb = dump.stat().st_size // (1024 * 1024)
      on_status(f"Scanning {dump.name} ({mb} MB) for key…")
    key = scan_dump(dump, verify)
    if key is not None:
      return key, dump
  return None


class RecoveryNeedsAdmin(Exception):
  """The updater must be launched + dumped, which requires elevation."""


def is_elevated() -> bool:
  """True if the current process has admin rights (Windows)."""
  try:
    import ctypes

    return bool(ctypes.windll.shell32.IsUserAnAdmin())
  except Exception:
    return False


def find_updater(install_dir: Path) -> Optional[Path]:
  """The client's AutoUpdate.exe in ``install_dir``, if present."""
  for name in ("AutoUpdate.exe", "AutoUpdatePlus.exe"):
    p = install_dir / name
    if p.is_file():
      return p
  return None


def recover_key(
  install_dir: Path,
  verify: Verify,
  wait: float = 8.0,
  allow_launch: bool = True,
  on_status: Optional[Callable[[str], None]] = None,
) -> Optional[bytes]:
  """Recover the archive key for a private server, escalating as needed.

  1. Scan existing dumps (safe, non-interactive).
  2. Else, if ``allow_launch`` and ``AutoUpdate.exe`` is present, launch it,
     dump it, and scan -- this needs elevation, so ``RecoveryNeedsAdmin`` is
     raised first when not elevated.

  Returns the key (also nothing is saved here -- the caller stores it), or
  ``None`` when no dump exists and there's no updater to launch.
  """
  import os

  def status(msg: str) -> None:
    if on_status is not None:
      on_status(msg)

  status("Scanning existing memory dumps…")
  found = recover_from_existing_dumps(verify, install_dir)
  if found is not None:
    return found[0]

  if not allow_launch:
    return None
  exe = find_updater(install_dir)
  if exe is None:
    return None
  if not is_elevated():
    raise RecoveryNeedsAdmin(
      f"Recovering this server's key means launching {exe.name}, which "
      "requires administrator rights. Restart elevated, or run "
      "'unsealed-reader recover-key' from an elevated terminal."
    )

  pid = created = None
  try:
    status(f"Launching {exe.name}; waiting {wait:.0f}s to unpack…")
    pid = launch(exe, wait)
    created = Path(os.environ.get("TEMP", ".")) / f"spakdump_{pid}.dmp"
    status("Snapshotting client memory…")
    create_full_dump(pid, created)
    status("Scanning for the key…")
    return scan_dump(created, verify)
  finally:
    if pid:
      kill(pid)
    if created and created.exists():
      try:
        created.unlink()
      except OSError:
        pass


# ── Windows: full-memory dump of a process (no external tools) ──


def _win():
  import ctypes
  from ctypes import wintypes

  return ctypes, wintypes


def find_pid(name: str) -> Optional[int]:
  ctypes, wintypes = _win()
  TH32CS_SNAPPROCESS = 0x2

  class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
      ("dwSize", wintypes.DWORD),
      ("cntUsage", wintypes.DWORD),
      ("th32ProcessID", wintypes.DWORD),
      ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
      ("th32ModuleID", wintypes.DWORD),
      ("cntThreads", wintypes.DWORD),
      ("th32ParentProcessID", wintypes.DWORD),
      ("pcPriClassBase", ctypes.c_long),
      ("dwFlags", wintypes.DWORD),
      ("szExeFile", ctypes.c_char * 260),
    ]

  k32 = ctypes.windll.kernel32
  snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
  entry = PROCESSENTRY32()
  entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
  found = None
  if k32.Process32First(snap, ctypes.byref(entry)):
    while True:
      if entry.szExeFile.decode("latin1").lower() == name.lower():
        found = entry.th32ProcessID
        break
      if not k32.Process32Next(snap, ctypes.byref(entry)):
        break
  k32.CloseHandle(snap)
  return found


def create_full_dump(pid: int, out_path: Path) -> Path:
  """Snapshot a process's full memory via dbghelp!MiniDumpWriteDump."""
  ctypes, wintypes = _win()
  PROCESS_ALL_ACCESS = 0x1F0FFF
  MiniDumpWithFullMemory = 0x2

  k32 = ctypes.windll.kernel32
  dbghelp = ctypes.windll.dbghelp
  h = k32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
  if not h:
    raise OSError(
      f"OpenProcess({pid}) failed (err {ctypes.get_last_error()}); "
      "run from an elevated shell if the target is elevated"
    )
  f = k32.CreateFileW(str(out_path), 0x40000000, 0, None, 2, 0x80, None)
  if f in (-1, wintypes.HANDLE(-1).value):
    k32.CloseHandle(h)
    raise OSError(f"CreateFile {out_path} failed")
  ok = dbghelp.MiniDumpWriteDump(h, pid, f, MiniDumpWithFullMemory, None, None, None)
  k32.CloseHandle(f)
  k32.CloseHandle(h)
  if not ok:
    raise OSError(f"MiniDumpWriteDump failed (err {ctypes.get_last_error()})")
  return out_path


def launch(exe: Path, wait: float) -> int:
  """Start ``exe``, wait for the protector to unpack, return its pid."""
  import subprocess

  try:
    proc = subprocess.Popen([str(exe)], cwd=str(exe.parent))
  except OSError as e:
    if getattr(e, "winerror", None) == 740:  # ERROR_ELEVATION_REQUIRED
      raise SystemExit(
        f"{exe.name} needs elevation (its manifest requires admin). Run this "
        f"from an elevated terminal, or start {exe.name} yourself and use "
        f"--process/--pid, or capture a dump and use --dump."
      )
    raise
  time.sleep(wait)
  return proc.pid


def kill(pid: int) -> None:
  ctypes, _ = _win()
  h = ctypes.windll.kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
  if h:
    ctypes.windll.kernel32.TerminateProcess(h, 0)
    ctypes.windll.kernel32.CloseHandle(h)
