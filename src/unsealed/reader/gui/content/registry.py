"""Format registry for the content area.

Maps a file extension to a handler that knows how to decode the file
into an Asset. Most formats then reflect over that Asset in a generic
tree; a handler may instead supply a custom `view` widget. Adding a
format is just registering a decode function (and optional view) — drop
a self-registering module under `handlers/`.

Everything here is expressed in terms of a `Resource` (the vfs handle):
a loose disk file is wrapped in a DiskSource-backed `Resource` at the
`MainWindow` boundary, so handlers, views and tabs never branch on
"disk vs archive" — the same code opens a file on disk and an entry
inside a mounted `.spak`.
"""

import re
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Pattern, Tuple

from ...vfs import Resource

# Decoders return an Asset, but some (e.g. .an1) return a list of them;
# the tree reflects over any object, so the return type stays open.
DecodeFn = Callable[[Resource], Any]


@dataclass(frozen=True)
class ContentContext:
  """What a custom view gets besides the decoded asset.

  `resource` is the opened file (disk or archive entry). `open_file`
  opens a (usually sibling) resource in a new tab — used by the map view
  to jump to an object's `.ms1`/`.tex`, and by the spak browser to open
  an archive entry.
  """

  resource: Resource
  open_file: Callable[[Resource], None]


# Optional custom view: (asset, context) -> QWidget. When absent, the
# content tab falls back to the generic AssetTree.
ViewFn = Callable[[Any, ContentContext], Any]


@dataclass(frozen=True)
class FormatHandler:
  name: str  # human label, e.g. "Mesh / Geometry"
  extensions: tuple[str, ...]  # lowercased, with dot: (".ms1",)
  decode: DecodeFn
  view: Optional[ViewFn] = None  # None = generic tree
  # Suffixes that vary by a numeric band (`.ed1` … `.ed17`) can't be
  # enumerated as fixed keys, so a handler may also claim filename
  # regexes. Mirrors `pipelines/main_pipeline.py:PATTERN_FILE_TYPES`.
  patterns: Tuple[str, ...] = ()


_HANDLERS: dict[str, FormatHandler] = {}
_PATTERNS: List[Tuple[Pattern[str], FormatHandler]] = []


def register(handler: FormatHandler) -> None:
  for ext in handler.extensions:
    _HANDLERS[ext.lower()] = handler
  for pattern in handler.patterns:
    _PATTERNS.append((re.compile(pattern, re.IGNORECASE), handler))


def for_resource(resource: Resource) -> Optional[FormatHandler]:
  """The handler for this resource: exact suffix first, then patterns."""
  handler = _HANDLERS.get(resource.suffix.lower())
  if handler is not None:
    return handler
  return next((h for pat, h in _PATTERNS if pat.search(resource.name)), None)
