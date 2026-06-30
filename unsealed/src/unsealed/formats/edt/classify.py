"""Classify a decoded .edt payload to a sensible output extension.

A decoded .edt is often still a proprietary Seal format, so we pick the
extension from the content (rather than a "decoded_" prefix) and let the
right (future) decoder claim it:

  - a known Seal binary data-file header  -> "dat"
  - otherwise pure-ASCII text             -> "scr" (Seal script)
  - anything else                         -> "bin"
"""

import re

_HEADER_LEN = 64

# The first null-terminated header string of a Seal binary data file,
# e.g. "SealOnline MonsterDataFile v3", "Seal Online Item File v2",
# "Seal Online QuestFlagFile v1". The trailing version is printf %x
# (hex). "Seal Online" appears with or without the inner space.
_DAT_SIGNATURE = re.compile(rb"^Seal ?Online .*File v[0-9A-Fa-f]+", re.IGNORECASE)

# Printable ASCII plus the usual text whitespace.
_TEXT_BYTES = frozenset(b"\t\n\r\f\v") | frozenset(range(0x20, 0x7F))


def detect_extension(data: bytes) -> str:
  """Return the output extension (no dot) for decoded .edt bytes."""
  if not data:
    return "bin"

  first_str = data[:_HEADER_LEN].split(b"\x00", 1)[0]
  if _DAT_SIGNATURE.match(first_str):
    return "dat"

  body = data.rstrip(b"\x00")
  if body and all(b in _TEXT_BYTES for b in body):
    return "scr"

  return "bin"
