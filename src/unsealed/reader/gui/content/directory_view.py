"""A `Directory` archive -> an in-app member browser (opens members).

Shared by the flat, eagerly-decoded containers: `.mdt` (model data) and
`.edp` (EDT package). Unlike a `.spak` neither needs a mount worker, key
panel, or decrypt-on-demand — the handler decodes the whole `Directory`
up front and this view just lists it. Every member is mounted into one
`MemorySource` so a member's sibling lookups (`.ms1` -> `.bn1`/`.tex`)
resolve within the archive, and double-clicking a row opens that member
in a new tab.

Members are handed out exactly as they sit in the container, so whatever
handler claims the member's extension does the real work — an `.edp`'s
members are still `.edt`-encrypted and decrypt when opened, the same as
a loose shard on disk.
"""

from __future__ import annotations

from typing import List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
  QAbstractItemView,
  QHBoxLayout,
  QHeaderView,
  QLabel,
  QLineEdit,
  QTableWidget,
  QTableWidgetItem,
  QVBoxLayout,
  QWidget,
)

from ...assets.directory import Directory
from ...vfs import MemorySource, Resource
from .registry import ContentContext


def _human_size(n: int) -> str:
  size = float(n)
  for unit in ("B", "KB", "MB", "GB"):
    if size < 1024 or unit == "GB":
      return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
    size /= 1024
  return f"{n} B"


class _SizeItem(QTableWidgetItem):
  """Right-aligned size cell that sorts by raw byte count, not text."""

  def __init__(self, size: int) -> None:
    super().__init__(_human_size(size))
    self._size = size
    self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

  def __lt__(self, other: "QTableWidgetItem") -> bool:
    if isinstance(other, _SizeItem):
      return self._size < other._size
    return super().__lt__(other)


def _entries(directory: Directory) -> List[Tuple[str, bytes]]:
  """(name, bytes) per named member, rebuilding name.ext per blob."""
  out: List[Tuple[str, bytes]] = []
  for blob in directory.list:
    if getattr(blob, "value", None) is None or getattr(blob, "name", None) is None:
      continue
    ext = getattr(blob, "extension", None)
    name = f"{blob.name}.{ext}" if ext else blob.name
    out.append((name, blob.value))
  return out


class DirectoryView(QWidget):
  """A filterable table of the archive's members over a MemorySource."""

  def __init__(self, directory: Directory, ctx: ContentContext) -> None:
    super().__init__()
    self.setObjectName("spakView")  # reuse the archive-browser styling
    self._ctx = ctx

    members = _entries(directory)
    # One source for the whole archive so member-to-member sibling
    # reads (a .ms1 pulling its .bn1/.tex) resolve within it. Kept
    # alive by any opened member tab through its Resource, and by this
    # view meanwhile.
    self._source = MemorySource(
      {name: data for name, data in members}, label=ctx.resource.name
    )

    box = QVBoxLayout(self)
    box.setContentsMargins(12, 12, 12, 12)
    box.setSpacing(8)

    bar = QHBoxLayout()
    bar.setContentsMargins(0, 0, 0, 0)
    self._count = QLabel("")
    self._count.setObjectName("spakCount")
    self._search = QLineEdit()
    self._search.setObjectName("spakSearch")
    self._search.setPlaceholderText("Filter files…")
    self._search.setClearButtonEnabled(True)
    self._search.textChanged.connect(self._filter)
    bar.addWidget(self._count)
    bar.addStretch(1)
    bar.addWidget(self._search, stretch=1)

    self._table = QTableWidget(0, 2)
    self._table.setObjectName("spakTable")
    self._table.setHorizontalHeaderLabels(["Name", "Size"])
    self._table.verticalHeader().setVisible(False)
    self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    self._table.setShowGrid(False)
    self._table.setSortingEnabled(True)
    head = self._table.horizontalHeader()
    head.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    head.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    self._table.itemActivated.connect(self._open_item)  # double-click / Enter

    hint = QLabel("Double-click a file to open it in a new tab.")
    hint.setObjectName("spakStatus")

    box.addLayout(bar)
    box.addWidget(self._table, stretch=1)
    box.addWidget(hint)

    self._populate(members)

  def _populate(self, members: List[Tuple[str, bytes]]) -> None:
    self._table.setSortingEnabled(False)
    self._table.setRowCount(0)
    for name, data in members:
      row = self._table.rowCount()
      self._table.insertRow(row)
      name_item = QTableWidgetItem(name)
      name_item.setData(Qt.ItemDataRole.UserRole, name)
      self._table.setItem(row, 0, name_item)
      self._table.setItem(row, 1, _SizeItem(len(data)))
    self._table.setSortingEnabled(True)
    self._table.sortItems(0, Qt.SortOrder.AscendingOrder)
    n = len(members)
    self._count.setText(f"{n:,} file{'' if n == 1 else 's'}")

  def _filter(self, text: str) -> None:
    needle = text.strip().lower()
    for row in range(self._table.rowCount()):
      name = self._table.item(row, 0).text().lower()
      self._table.setRowHidden(row, bool(needle) and needle not in name)

  def _open_item(self, item) -> None:
    name = self._table.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
    self._ctx.open_file(Resource(self._source, name))
