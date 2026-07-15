"""`.edt` -> decrypt, classify, and show the converted result inline.

An `.edt` is an encrypted wrapper: decoded it becomes some *other* Seal
format (a `.dat` table, a `.scr`/`.tsv` cell table, XML, or opaque
binary — see `formats/edt/classify.py`). This view does the whole chain
automatically: it hands the decrypted bytes to the same handler that
would open a loose file of the detected type (via an in-memory
`Resource`), so the user sees the final table/preview, not the
ciphertext — with a slim banner noting what it decoded to. XML decodes
to its embedded-schema table like the others; only unrecognized binary
has no handler and falls back to text / hex.

The banner also switches between that parsed view and the decrypted
payload as it sits on disk — raw text or a hexdump — so a schema can be
checked against the bytes it was read from.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
  QButtonGroup,
  QHBoxLayout,
  QLabel,
  QPlainTextEdit,
  QPushButton,
  QStackedWidget,
  QVBoxLayout,
  QWidget,
)

from ...assets.edt import Edt
from ...vfs import MemorySource, Resource
from .registry import ContentContext, for_resource
from .tree import AssetTree, Node

# Human labels for the classified extension, shown in the banner.
_KIND = {
  "dat": "data table (.dat)",
  "scr": "script table (.scr)",
  "tsv": "tab table (.tsv)",
  "xml": "XML document",
  "bin": "binary (unrecognized)",
}


def _decode_text(data: bytes) -> str:
  for enc in ("utf-8", "euc_kr", "cp1252"):
    try:
      return data.decode(enc)
    except (UnicodeDecodeError, LookupError):
      continue
  return data.decode("latin-1", "replace")


def _hexdump(data: bytes, limit: int = 1 << 18) -> str:
  lines = []
  for off in range(0, min(len(data), limit), 16):
    chunk = data[off : off + 16]
    hexs = " ".join(f"{b:02x}" for b in chunk)
    ascii_ = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in chunk)
    lines.append(f"{off:08x}  {hexs:<47}  {ascii_}")
  if len(data) > limit:
    lines.append(f"… ({len(data) - limit:,} more bytes)")
  return "\n".join(lines)


def _text_preview(text: str) -> QPlainTextEdit:
  view = QPlainTextEdit(text)
  view.setObjectName("edtText")
  view.setReadOnly(True)
  view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
  return view


def _inner_view(
  name: str, data: bytes, ext: str, ctx: ContentContext
) -> tuple[QWidget, str]:
  """Open the decrypted bytes as if they were a loose file of `ext`.

  Returns the widget plus a label describing what it actually shows, so
  the banner and content agree (a `bin` payload that reads as text is
  labelled as such rather than "binary")."""
  source = MemorySource({name: data}, label=ctx.resource.name)
  resource = Resource(source, name)

  handler = for_resource(resource)
  if handler is not None:
    asset = handler.decode(resource)
    inner_ctx = ContentContext(resource, ctx.open_file)
    widget = (
      handler.view(asset, inner_ctx)
      if handler.view is not None
      else AssetTree(Node(handler.name, asset, handler.name))
    )
    return widget, _KIND.get(ext, ext)

  # No handler for this kind (xml / bin): text or hex preview.
  if ext == "xml":
    return _text_preview(_decode_text(data)), _KIND["xml"]
  if data and _looks_textual(data):
    return _text_preview(_decode_text(data)), "text (from binary)"
  return _text_preview(_hexdump(data)), _KIND["bin"]


def _looks_textual(data: bytes) -> bool:
  """True if the bytes read as (possibly EUC-KR) text, not binary.

  An ASCII-only check would misjudge Korean dialogue (its EUC-KR bytes
  sit in the high range) as binary, so decode first and judge the
  string: little control-char / replacement noise means real text."""
  if not data:
    return False
  text = _decode_text(data[:4096])
  if not text:
    return False
  bad = sum(1 for ch in text if (ord(ch) < 0x20 and ch not in "\t\n\r") or ch == "�")
  return bad / len(text) < 0.05


class _Lazy(QWidget):
  """Builds its child the first time the page is shown."""

  def __init__(self, build: Callable[[], QWidget]) -> None:
    super().__init__()
    self._build = build
    self._layout = QVBoxLayout(self)
    self._layout.setContentsMargins(0, 0, 0, 0)

  def showEvent(self, event) -> None:
    if self._build is not None:
      self._layout.addWidget(self._build())
      self._build = None
    super().showEvent(event)


class EdtView(QWidget):
  """Banner ("decoded to …") + view switcher over the inner view.

  Three pages share the one decrypted payload: the parsed view a loose
  file of the detected type would get, the payload as text, and a
  hexdump. The raw pages are built lazily — a multi-MB hexdump is not
  worth formatting for a user who only wanted the table."""

  def __init__(self, edt: Edt, ctx: ContentContext) -> None:
    super().__init__()
    self.setObjectName("edtView")
    self._data = edt.value or b""
    ext = (edt.extension or "bin").lower()
    stem = edt.name or ctx.resource.stem
    name = f"{stem}.{ext}"

    try:
      inner, kind = _inner_view(name, self._data, ext, ctx)
    except Exception as exc:  # a bad inner decode shouldn't lose the banner
      inner = _text_preview(f"Couldn't open the decoded {ext!r} content:\n\n{exc}")
      kind = _KIND.get(ext, ext)

    self._stack = QStackedWidget()
    self._stack.addWidget(inner)
    self._stack.addWidget(_Lazy(lambda: _text_preview(_decode_text(self._data))))
    self._stack.addWidget(_Lazy(lambda: _text_preview(_hexdump(self._data))))

    label = QLabel(f"Decrypted .edt  →  {kind}   ·   {len(self._data):,} bytes")
    label.setObjectName("edtBannerLabel")

    banner = QWidget()
    banner.setObjectName("edtBanner")
    row = QHBoxLayout(banner)
    row.setContentsMargins(12, 6, 12, 6)
    row.setSpacing(6)
    row.addWidget(label)
    row.addStretch(1)
    self._buttons = QButtonGroup(self)
    self._buttons.setExclusive(True)
    for index, text in enumerate(("Parsed", "Raw", "Hex")):
      button = QPushButton(text)
      button.setObjectName("edtModeButton")
      button.setCheckable(True)
      button.setChecked(index == 0)
      self._buttons.addButton(button, index)
      row.addWidget(button)
    self._buttons.idClicked.connect(self._stack.setCurrentIndex)

    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(banner)
    layout.addWidget(self._stack, stretch=1)
