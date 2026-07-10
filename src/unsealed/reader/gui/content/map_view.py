"""Map overview: a sidebar of sections over a stacked content pane.

A `.map` (Terrain) has several distinct concerns — properties, placed
objects, textures, heightmap — so instead of one long list we give each
its own section. Objects and textures can be opened as their own files
in a new tab; selecting an object shows where it's placed.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
  QAbstractItemView,
  QHBoxLayout,
  QHeaderView,
  QLabel,
  QListWidget,
  QPushButton,
  QSplitter,
  QStackedWidget,
  QTableWidget,
  QTableWidgetItem,
  QVBoxLayout,
  QWidget,
)

from ...assets.terrain import Terrain
from ...vfs import Resource
from .properties import PropertiesView
from .registry import ContentContext

# Keep per-object placement lists snappy and un-overwhelming.
_MAX_POSITIONS = 500


def _basename(name: str) -> str:
  return name.strip().replace("\\", "/").split("/")[-1]


def _fmt_vec(values: list[float]) -> str:
  return ", ".join(f"{v:.2f}" for v in values)


def _resolve_texture(base: Resource, name: str) -> Resource:
  # Maps store the original art name (e.g. tile.tga); the packed file is
  # the encrypted .tex/.te1 with the same stem (on disk or in the same
  # archive). Prefer those.
  leaf = _basename(name)
  stem = Path(leaf).stem
  for ext in (".tex", ".te1"):
    candidate = base.with_name(stem + ext)
    if candidate.exists():
      return candidate
  return base.with_name(leaf)


def _table(headers: list[str]) -> QTableWidget:
  table = QTableWidget(0, len(headers))
  table.setObjectName("mapTable")
  table.setHorizontalHeaderLabels(headers)
  table.verticalHeader().setVisible(False)
  table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
  table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
  table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
  table.setShowGrid(False)
  return table


def _cell(text: str) -> QTableWidgetItem:
  item = QTableWidgetItem(text)
  item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
  return item


class ObjectsPage(QWidget):
  """Unique object files (left) and, per selection, their placements."""

  def __init__(self, terrain: Terrain, ctx: ContentContext) -> None:
    super().__init__()
    self._terrain = terrain
    self._ctx = ctx
    self._current: str | None = None

    self._by_idx: dict[int, list] = {}
    for obj in terrain.objects:
      self._by_idx.setdefault(obj["idx"], []).append(obj)

    self._files = _table(["Object", "Instances"])
    head = self._files.horizontalHeader()
    head.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    head.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    for i, name in enumerate(terrain.object_files):
      row = self._files.rowCount()
      self._files.insertRow(row)
      self._files.setItem(row, 0, _cell(_basename(name)))
      self._files.setItem(row, 1, _cell(str(len(self._by_idx.get(i, [])))))
    self._files.currentCellChanged.connect(self._on_select)
    self._files.cellDoubleClicked.connect(lambda *_: self._open())

    self._name = QLabel("Select an object")
    self._name.setObjectName("mapDetailName")
    self._open_btn = QPushButton("Open in new tab")
    self._open_btn.setObjectName("mapOpenButton")
    self._open_btn.setEnabled(False)
    self._open_btn.clicked.connect(self._open)
    header = QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)
    header.addWidget(self._name)
    header.addStretch(1)
    header.addWidget(self._open_btn)

    self._positions = _table(["#", "Position", "Rotation"])
    phead = self._positions.horizontalHeader()
    phead.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    phead.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    phead.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

    detail = QWidget()
    detail_layout = QVBoxLayout(detail)
    detail_layout.setContentsMargins(0, 0, 0, 0)
    detail_layout.setSpacing(8)
    detail_layout.addLayout(header)
    detail_layout.addWidget(self._positions)

    split = QSplitter(Qt.Orientation.Horizontal)
    split.addWidget(self._files)
    split.addWidget(detail)
    split.setStretchFactor(0, 3)
    split.setStretchFactor(1, 4)
    split.setSizes([340, 460])

    layout = QVBoxLayout(self)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.addWidget(split)

  def _on_select(self, row: int, *_args) -> None:
    if row < 0 or row >= len(self._terrain.object_files):
      return
    self._current = _basename(self._terrain.object_files[row])
    self._name.setText(self._current)
    self._open_btn.setEnabled(True)
    self._fill_positions(self._by_idx.get(row, []))

  def _fill_positions(self, placements: list) -> None:
    self._positions.setRowCount(0)
    for n, obj in enumerate(placements[:_MAX_POSITIONS], start=1):
      row = self._positions.rowCount()
      self._positions.insertRow(row)
      self._positions.setItem(row, 0, _cell(str(n)))
      self._positions.setItem(row, 1, _cell(_fmt_vec(obj["pos"])))
      self._positions.setItem(row, 2, _cell(_fmt_vec(obj["rot"])))
    hidden = len(placements) - _MAX_POSITIONS
    if hidden > 0:
      row = self._positions.rowCount()
      self._positions.insertRow(row)
      self._positions.setItem(row, 0, _cell("…"))
      self._positions.setItem(row, 1, _cell(f"{hidden} more placements"))

  def _open(self) -> None:
    if self._current:
      self._ctx.open_file(self._ctx.resource.with_name(self._current))


class TexturesPage(QWidget):
  """Textures (and the lightmap), each openable as its own file."""

  def __init__(self, terrain: Terrain, ctx: ContentContext) -> None:
    super().__init__()
    self._ctx = ctx
    self._names: list[str] = []

    self._open_btn = QPushButton("Open in new tab")
    self._open_btn.setObjectName("mapOpenButton")
    self._open_btn.setEnabled(False)
    self._open_btn.clicked.connect(self._open)
    toolbar = QHBoxLayout()
    toolbar.setContentsMargins(0, 0, 0, 0)
    toolbar.addStretch(1)
    toolbar.addWidget(self._open_btn)

    self._table = _table(["Texture", "Role"])
    thead = self._table.horizontalHeader()
    thead.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    thead.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    for name in terrain.textures:
      self._add_row(name, "tile")
    if terrain.lightmap:
      self._add_row(terrain.lightmap, "lightmap")
    self._table.currentCellChanged.connect(
      lambda row, *_: self._open_btn.setEnabled(row >= 0)
    )
    self._table.cellDoubleClicked.connect(lambda *_: self._open())

    layout = QVBoxLayout(self)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)
    layout.addLayout(toolbar)
    layout.addWidget(self._table)

  def _add_row(self, name: str, role: str) -> None:
    row = self._table.rowCount()
    self._table.insertRow(row)
    self._table.setItem(row, 0, _cell(_basename(name)))
    self._table.setItem(row, 1, _cell(role))
    self._names.append(name)

  def _open(self) -> None:
    row = self._table.currentRow()
    if 0 <= row < len(self._names):
      self._ctx.open_file(_resolve_texture(self._ctx.resource, self._names[row]))


class MapView(QWidget):
  """Sidebar sections (Overview / Objects / Textures / Heightmap)."""

  def __init__(self, terrain: Terrain, ctx: ContentContext) -> None:
    super().__init__()
    self.setObjectName("mapView")
    self._terrain = terrain

    self._nav = QListWidget()
    self._nav.setObjectName("mapNav")
    self._nav.setFixedWidth(190)
    self._pages = QStackedWidget()

    self._add("Overview", self._overview())
    self._add(f"Objects · {len(terrain.object_files)}", ObjectsPage(terrain, ctx))
    self._add(f"Textures · {len(terrain.textures)}", TexturesPage(terrain, ctx))
    self._add("Heightmap", self._heightmap())

    self._nav.currentRowChanged.connect(self._pages.setCurrentIndex)
    self._nav.setCurrentRow(0)

    layout = QHBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(self._nav)
    layout.addWidget(self._pages, stretch=1)

  def _add(self, label: str, page: QWidget) -> None:
    self._nav.addItem(label)
    self._pages.addWidget(page)

  def _overview(self) -> PropertiesView:
    t = self._terrain
    total = len(t.walkable)
    blocked = sum(1 for w in t.walkable if w) if t.walkable else 0
    walkable = f"{total - blocked:,} of {total:,}" if total else "—"
    map_rows = [
      ("Name", t.name),
      ("Version", f"v.{t.version}"),
      ("Dimensions", f"{t.width} × {t.height}"),
      ("Terrain grid", str(t.terrain_grid)),
      ("Lightmap", _basename(t.lightmap) if t.lightmap else "—"),
    ]
    content_rows = [
      ("Object instances", f"{len(t.objects):,}"),
      ("Unique objects", f"{len(t.object_files):,}"),
      ("Textures", f"{len(t.textures):,}"),
      ("Walkable tiles", walkable),
    ]
    return PropertiesView([("Map", map_rows), ("Content", content_rows)])

  def _heightmap(self) -> PropertiesView:
    t = self._terrain
    hm = t.heightmap
    if hm:
      rows = [
        ("Samples", f"{len(hm):,}"),
        ("Grid", f"{t.width} × {t.height}"),
        ("Min height", f"{min(hm):.3f}"),
        ("Max height", f"{max(hm):.3f}"),
        ("Average", f"{sum(hm) / len(hm):.3f}"),
      ]
    else:
      rows = [("Samples", "0")]
    return PropertiesView([("Heightmap", rows)])
