"""Recover a private-server .spak key by a known-plaintext attack.

No memory dump and no reference client: a few tiny plaintext snippets
are embedded (``spak_anchors``) -- short fragments of the deflate
stream of files byte-identical across Seal Online builds. We match one
to an entry in the target by its cleartext CRC-32, hand that entry's
ciphertext plus the snippet to the bundled ``bkcrack``, and it recovers
the three ZipCrypto internal keys -- shared by every entry of that
server, so one crack unlocks all its archives. Cross-platform; the only
dependency, bkcrack, is vendored (see ``reader/vendor``).

The snippets are short prefixes, never whole files, so nothing
copyrightable can be reconstructed from them.

``crack`` is the single entry point: ``SpakArchive._resolve_key`` calls
it during mount so the reader, GUI, and viewer all recover a private
key automatically -- there is no standalone command.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import threading
import zipfile
from pathlib import Path
from typing import Callable, Iterator, List, Optional

from ..assets.spak_keystore import KeyTriple
from ..vendor import BkcrackUnavailable, bkcrack_path
from . import spak_anchors

Status = Callable[[str], None]
# ``on_progress(fraction, label)`` -- fraction in 0..1 over the whole
# crack, label a short human phase ("Analyzing…", "Recovering key…").
Progress = Callable[[float, str], None]

# bkcrack should crack a valid pair in seconds; cap it so a bad match
# (wrong deflate settings) can't wedge the run.
_BKCRACK_TIMEOUT = 600

# A bkcrack progress tick, e.g. " 12.3 % (1234 / 10000)".
_PCT = re.compile(r"\s*([\d.]+)\s*%")
# The reduction phase is quick; give it the first slice of the bar and
# let the (slow) attack phase fill the rest.
_REDUCTION_SPAN = 0.15


def _parse_keys(out: str) -> List[KeyTriple]:
  """Key triples printed after bkcrack's ``Keys`` line (deduped)."""
  pos = out.find("Keys")
  if pos < 0:
    return []
  found: List[KeyTriple] = []
  for m in re.findall(r"([0-9a-fA-F]{8}) ([0-9a-fA-F]{8}) ([0-9a-fA-F]{8})", out[pos:]):
    triple = (int(m[0], 16), int(m[1], 16), int(m[2], 16))
    if triple not in found:
      found.append(triple)
  return found


def _iter_tokens(stream) -> Iterator[str]:
  """Yield bkcrack output split on CR *and* LF.

  bkcrack redraws its progress counter with a carriage return, so a
  plain line iterator would swallow every tick into one giant line.
  """
  buf = ""
  while True:
    ch = stream.read(1)
    if not ch:
      break
    if ch in "\r\n":
      if buf:
        yield buf
      buf = ""
    else:
      buf += ch
  if buf:
    yield buf


def _run_bkcrack(
  cipher: bytes, plain: bytes, on_progress: Optional[Progress] = None
) -> List[KeyTriple]:
  """Recover candidate keys from one ciphertext/plaintext pair.

  Streams bkcrack's stdout so a UI can show live progress instead of
  appearing to hang for the ~10s the attack takes.
  """
  bk = bkcrack_path()
  report = on_progress or (lambda _f, _l: None)
  killed = {"v": False}
  lines: List[str] = []
  phase = "reduction"

  with tempfile.TemporaryDirectory(prefix="unsealed-bk-") as d:
    cp = Path(d) / "cipher.bin"
    pp = Path(d) / "plain.bin"
    cp.write_bytes(cipher)
    pp.write_bytes(plain)
    proc = subprocess.Popen(
      [str(bk), "-c", str(cp), "-p", str(pp)],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
      bufsize=1,
    )

    def _kill() -> None:
      killed["v"] = True
      proc.kill()

    timer = threading.Timer(_BKCRACK_TIMEOUT, _kill)
    timer.start()
    try:
      for token in _iter_tokens(proc.stdout):
        lines.append(token)
        low = token.lower()
        if "reduction" in low:
          phase = "reduction"
          report(0.0, "Analyzing…")
        elif "attack on" in low:
          phase = "attack"
          report(_REDUCTION_SPAN, "Recovering key…")
        else:
          m = _PCT.match(token)
          if m:
            pct = min(float(m.group(1)) / 100.0, 1.0)
            if phase == "reduction":
              report(_REDUCTION_SPAN * pct, "Analyzing…")
            else:
              report(_REDUCTION_SPAN + (1.0 - _REDUCTION_SPAN) * pct, "Recovering key…")
      proc.wait()
    finally:
      timer.cancel()

  if killed["v"]:
    return []
  return _parse_keys("\n".join(lines))


def crack(
  infos: List[zipfile.ZipInfo],
  read_ciphertext: Callable[[zipfile.ZipInfo], bytes],
  verify: Callable[[KeyTriple], bool],
  on_status: Optional[Status] = None,
  on_progress: Optional[Progress] = None,
) -> Optional[KeyTriple]:
  """Recover the key triple from an archive's entries, or ``None``.

  ``infos`` are the archive's ``ZipInfo`` list;
  ``read_ciphertext(info)`` returns an entry's raw stored bytes (12-byte
  ZipCrypto header + encrypted payload); ``verify(keys)`` CRC-gates a
  candidate. Returns ``None`` when no embedded anchor matches (nothing
  to attack).

  Raises :class:`BkcrackUnavailable` if bkcrack isn't bundled for the
  host -- callers treat that as "couldn't auto-recover".
  """
  status = on_status or (lambda _m: None)
  by_crc = {}
  for i in infos:
    if not i.is_dir() and i.flag_bits & 0x1 and i.compress_type == zipfile.ZIP_DEFLATED:
      by_crc.setdefault((i.CRC, i.file_size), i)
  if not by_crc:
    return None

  for anchor in spak_anchors.ANCHORS:
    info = by_crc.get((anchor.crc, anchor.usize))
    # Require the same compressed length: then the target's deflate
    # stream equals the anchor's, so the snippet is a valid prefix.
    if info is None or info.compress_size - 12 != anchor.comp_len:
      continue
    status(f"Recovering key from {info.filename} ({anchor.archive})…")
    cipher = read_ciphertext(info)
    for keys in _run_bkcrack(cipher, anchor.snippet, on_progress):
      if verify(keys):
        return keys
  return None


__all__ = ["crack", "BkcrackUnavailable", "KeyTriple"]
