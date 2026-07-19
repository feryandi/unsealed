"""Classify a decoded .edt payload to a sensible output extension.

A decoded .edt is often still a proprietary Seal format, so we pick the
extension from the content (rather than a "decoded_" prefix) and let the
right (future) decoder claim it:

  - a known Seal binary data-file header  -> "dat"
  - an XML declaration (<?xml ...)         -> "xml"
  - text with tab-delimited rows           -> "tsv"
  - otherwise text                         -> "scr" (Seal script)
  - anything else                         -> "bin"

"Text" here means EUC-KR text, NOT ASCII: the game is Korean. An earlier
ASCII-only rule sent every table containing Hangul to "bin", which quietly
lost eight of them -- `npctalk` (a 3927-tab `BEGIN`/`TALK` table),
`itemtrademall` (a 313-row pipe table), `m_hair1`/`w_hair1`, `map_info`,
`pettalk`, `usa` and `p_newevolution_result`. They decode cleanly as
cp949/EUC-KR; only the classifier disagreed.

High bytes are therefore text. What still separates real binary is CONTROL
bytes, and it separates it cleanly: the four genuinely-binary payloads here
are riddled with them (`iteminfo`/`piteminfo` carry ~5M each,
`newcontroll`/`oldcontroll` ~10 in 116 bytes), while all eight text files
have exactly zero.
"""

import re

_HEADER_LEN = 64

# The first null-terminated header string of a Seal binary data file,
# e.g. "SealOnline MonsterDataFile v3", "Seal Online Item File v2",
# "Seal Online QuestFlagFile v1". The trailing version is printf %x
# (hex). "Seal Online" appears with or without the inner space.
_DAT_SIGNATURE = re.compile(rb"^Seal ?Online .*v[0-9A-Fa-f]+", re.IGNORECASE)

# Printable ASCII + the usual text whitespace + the high half (EUC-KR lead
# and trail bytes -- the game's text is Korean, see the module docstring).
# Deliberately NOT ASCII-only; control bytes are what mark a payload binary.
_TEXT_BYTES = (
  frozenset(b"\t\n\r\f\v")
  | frozenset(range(0x20, 0x7F))
  | frozenset(range(0x80, 0x100))
)


def detect_extension(data: bytes) -> str:
  """Return the output extension (no dot) for decoded .edt bytes."""
  if not data:
    return "bin"

  # A genuine binary .dat carries its title as a NUL-terminated string in a
  # 64-byte header block (title + NUL padding), so a NUL is always present.
  # A text file may merely open with a version-like line -- `worldmap`'s
  # "Seal Online WorldmapWarp v1\r\n29\r\n1|2|..." matches the signature but
  # is really a pipe table -- so require the NUL to avoid claiming it as dat.
  header = data[:_HEADER_LEN]
  first_str = header.split(b"\x00", 1)[0]
  if b"\x00" in header and _DAT_SIGNATURE.match(first_str):
    return "dat"

  if data.lstrip()[:5].lower() == b"<?xml":
    return "xml"

  body = data.rstrip(b"\x00")
  if body and all(b in _TEXT_BYTES for b in body):
    # Pipe-delimited tables + string lists are `.scr`; a tab-delimited
    # table (no `|`) is a generic `.tsv` (guarder/polymorph/...).
    if b"|" not in body and b"\t" in body:
      return "tsv"
    return "scr"

  return "bin"
