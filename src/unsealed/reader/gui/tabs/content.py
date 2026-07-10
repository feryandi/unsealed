import traceback
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from ...vfs import Resource
from ..content import AssetTree, ContentContext, Node, for_resource


class ContentTab(QWidget):
  """One opened file: decodes it and mounts its asset tree.

  Always closable (even when it's the only tab): closing the last one
  returns to the welcome screen.

  The file is a vfs `Resource` — a loose disk file (wrapped by
  `MainWindow`) or an entry inside a mounted `.spak` — so the same
  handlers open both. Falls back to a placeholder for formats without a
  handler yet, or an error view (with traceback) when decoding fails —
  both useful when the point is to debug a file's structure.
  """

  def __init__(
    self,
    resource: Resource,
    output_dir: Path | None = None,
    open_file: Callable[[Resource], None] | None = None,
  ) -> None:
    super().__init__()
    self.resource = resource
    self.output_dir = output_dir
    self._open_file = open_file or (lambda _r: None)
    self.setObjectName("contentTab")

    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(self._build_body())

  def _build_body(self) -> QWidget:
    handler = for_resource(self.resource)
    if handler is None:
      return self._placeholder(
        f"File format: {self.resource.suffix or 'this'} is not supported."
      )
    try:
      asset = handler.decode(self.resource)
      if handler.view is not None:
        return handler.view(asset, ContentContext(self.resource, self._open_file))
      return AssetTree(Node(handler.name, asset, handler.name))
    except Exception:
      return self._error(traceback.format_exc())

  def _placeholder(self, message: str) -> QWidget:
    label = QLabel(message)
    label.setObjectName("contentPlaceholder")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setWordWrap(True)
    return label

  def _error(self, tb: str) -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(8)
    heading = QLabel(f"Couldn't decode {self.resource.name}")
    heading.setObjectName("errorHeading")
    trace = QPlainTextEdit(tb)
    trace.setObjectName("errorTrace")
    trace.setReadOnly(True)
    layout.addWidget(heading)
    layout.addWidget(trace, stretch=1)
    return box

  @property
  def title(self) -> str:
    return self.resource.name
