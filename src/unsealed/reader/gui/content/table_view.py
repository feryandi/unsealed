"""Grid view for schema-driven tables (`.dat`/`.scr`/`.tsv`).

Renders whatever a `table_sources` adapter produces and lets the user
switch the schema applied to the data. The picker defaults to the
schema the decoder matched by filename/type; it lists only schemas whose
column count fits the data (a "Show all" toggle reveals the rest), and
its combo is search-as-you-type so a schema is easy to find by name.
"""

from __future__ import annotations

from typing import List

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
  QAbstractItemView,
  QCheckBox,
  QComboBox,
  QCompleter,
  QHBoxLayout,
  QHeaderView,
  QLabel,
  QTableView,
  QVBoxLayout,
  QWidget,
)

from .table_sources import SchemaOption, TableData


class _TableModel(QAbstractTableModel):
  """A read-only model over a flat string grid (no per-cell widgets)."""

  def __init__(self) -> None:
    super().__init__()
    self._columns: List[str] = []
    self._rows: List[List[str]] = []

  def set_grid(self, columns: List[str], rows: List[List[str]]) -> None:
    self.beginResetModel()
    self._columns = columns
    self._rows = rows
    self.endResetModel()

  def rowCount(self, parent=QModelIndex()) -> int:
    return 0 if parent.isValid() else len(self._rows)

  def columnCount(self, parent=QModelIndex()) -> int:
    return 0 if parent.isValid() else len(self._columns)

  def data(self, index, role=Qt.ItemDataRole.DisplayRole):
    if role != Qt.ItemDataRole.DisplayRole or not index.isValid():
      return None
    row = self._rows[index.row()]
    col = index.column()
    return row[col] if col < len(row) else ""

  def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
    if role != Qt.ItemDataRole.DisplayRole:
      return None
    if orientation == Qt.Orientation.Horizontal:
      return self._columns[section] if section < len(self._columns) else ""
    return section  # 0-based row index down the side


class TableView(QWidget):
  """Schema picker over a data grid."""

  def __init__(self, adapter) -> None:
    super().__init__()
    self.setObjectName("tableView")
    self._adapter = adapter
    self._options: List[SchemaOption] = adapter.options()
    self._current = adapter.default_label

    self._model = _TableModel()
    self._table = QTableView()
    self._table.setObjectName("dataTable")
    self._table.setModel(self._model)
    self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    self._table.setAlternatingRowColors(True)
    self._table.setShowGrid(False)
    self._table.horizontalHeader().setSectionResizeMode(
      QHeaderView.ResizeMode.Interactive
    )
    self._table.horizontalHeader().setStretchLastSection(True)
    self._table.verticalHeader().setDefaultSectionSize(22)

    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(self._build_bar())
    layout.addWidget(self._table, stretch=1)

    self._populate_combo()
    self._apply(self._current)

  # ── schema bar ────────────────────────────────────────────────────

  def _build_bar(self) -> QWidget:
    bar = QWidget()
    bar.setObjectName("tableBar")
    box = QHBoxLayout(bar)
    box.setContentsMargins(12, 8, 12, 8)
    box.setSpacing(10)

    label = QLabel("Schema")
    label.setObjectName("tableBarLabel")

    self._combo = QComboBox()
    self._combo.setObjectName("schemaCombo")
    self._combo.setEditable(True)
    self._combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    self._combo.setMinimumWidth(260)
    self._combo.lineEdit().setPlaceholderText("Search schemas or version…")
    completer = self._combo.completer()
    completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    # Select by schema name held in the item's data (the display text
    # also carries the version, so the completer can search "v12" too).
    self._combo.activated.connect(self._on_pick)

    self._show_all = QCheckBox("Show all")
    self._show_all.setObjectName("tableShowAll")
    self._show_all.setToolTip("Include schemas whose column count doesn't match")
    self._show_all.toggled.connect(lambda _: self._populate_combo())

    self._info = QLabel("")
    self._info.setObjectName("tableInfo")

    box.addWidget(label)
    box.addWidget(self._combo)
    box.addWidget(self._show_all)
    box.addStretch(1)
    box.addWidget(self._info)
    return bar

  @staticmethod
  def _display(option: SchemaOption) -> str:
    return f"{option.label}   ·   {option.version}" if option.version else option.label

  def _visible_options(self) -> List[SchemaOption]:
    show_all = self._show_all.isChecked()
    return [o for o in self._options if show_all or o.fits or o.label == self._current]

  def _populate_combo(self) -> None:
    self._combo.blockSignals(True)
    self._combo.clear()
    for option in self._visible_options():
      self._combo.addItem(self._display(option), userData=option.label)
    self._select_current()
    self._combo.blockSignals(False)

  def _select_current(self) -> None:
    index = self._combo.findData(self._current)
    if index >= 0:
      self._combo.setCurrentIndex(index)

  def _on_pick(self, index: int) -> None:
    label = self._combo.itemData(index)
    if label and label != self._current:
      self._apply(label)

  # ── data ──────────────────────────────────────────────────────────

  def _apply(self, label: str) -> None:
    try:
      data = self._adapter.apply(label)
    except Exception as exc:  # a mismatched schema can over-read; surface it
      data = TableData([], [], note=f"can't apply '{label}': {exc}")
    self._current = label
    self._model.set_grid(data.columns, data.rows)
    self._table.scrollToTop()
    self._set_info(data)
    self._select_current()  # keep the combo in sync with an apply from code

  def _set_info(self, data: TableData) -> None:
    if data.note:
      self._info.setText(data.note)
      return
    shown = len(data.rows)
    suffix = " (truncated)" if data.truncated else ""
    self._info.setText(f"{shown:,} rows × {len(data.columns)} cols{suffix}")
