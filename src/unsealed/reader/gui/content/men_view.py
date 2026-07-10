"""`.men` UI files -> an element tree + per-element properties panel.

A `.men` describes a nested tree of UI elements (images, buttons, …),
each with a screen rectangle and a set of sprite indices into a `.spr`
sheet. This view mirrors that tree on the left; selecting an element
shows its properties (position/size, sprite state indices, …) on the
right and lets you open the sprite sheet it references — either the
element's own `spr_file` (v6+) or the file-level `spr` — in a new tab.
Opening that `.spr` in turn surfaces its textures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
  QHBoxLayout,
  QLabel,
  QPushButton,
  QSplitter,
  QTreeWidget,
  QTreeWidgetItem,
  QVBoxLayout,
  QWidget,
)

from ...vfs import Resource
from .properties import PropertiesView
from .registry import ContentContext

# UI-state sprite indices a .men element can carry, in the order shown.
_STATE_KEYS: List[tuple[str, str]] = [
  ("Base", "ui_base_spr_idx"),
  ("Click", "ui_click_spr_idx"),
  ("Disabled", "ui_disabled_spr_idx"),
  ("Hover", "ui_hover_spr_idx"),
  ("Focus", "ui_focus_spr_idx"),
]


def _element_label(element: Dict[str, Any]) -> str:
  label = str(element.get("label") or "").strip()
  return label or "(unnamed)"


def _spr_for(element: Dict[str, Any], file_spr: str) -> str:
  """The .spr this element draws from: its own (v6+) or the file's."""
  own = element.get("spr_file")
  return str(own).strip() if own else file_spr


class _ElementItem(QTreeWidgetItem):
  """A tree row bound to its decoded element dict."""

  def __init__(self, element: Dict[str, Any]) -> None:
    super().__init__()
    self.element = element
    self.setText(0, _element_label(element))
    self.setText(1, str(element.get("type") or ""))


class MenView(QWidget):
  """Element tree (left) + properties / open-sprite panel (right)."""

  def __init__(self, parsed: Dict[str, Any], ctx: ContentContext) -> None:
    super().__init__()
    self.setObjectName("menView")
    self._ctx = ctx
    self._file_spr = str(parsed.get("spr") or "").strip()
    self._version = int(parsed.get("version") or 0)
    self._selected: Optional[Dict[str, Any]] = None

    self._tree = QTreeWidget()
    self._tree.setObjectName("assetTree")
    self._tree.setColumnCount(2)
    self._tree.setHeaderLabels(["Element", "Type"])
    self._tree.setUniformRowHeights(True)
    self._tree.setColumnWidth(0, 240)
    self._build_tree(parsed.get("elements") or [])
    self._tree.currentItemChanged.connect(self._on_select)

    # Right panel: header, open-sprite button, then a swappable props.
    self._name = QLabel("Select an element")
    self._name.setObjectName("mapDetailName")
    self._open_btn = QPushButton("Open sprite sheet (.spr)")
    self._open_btn.setObjectName("mapOpenButton")
    self._open_btn.setEnabled(False)
    self._open_btn.clicked.connect(self._open_spr)
    header = QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)
    header.addWidget(self._name)
    header.addStretch(1)
    header.addWidget(self._open_btn)

    self._props_holder = QVBoxLayout()
    self._props_holder.setContentsMargins(0, 0, 0, 0)
    self._props: QWidget = self._file_properties()
    self._props_holder.addWidget(self._props)

    detail = QWidget()
    detail_layout = QVBoxLayout(detail)
    detail_layout.setContentsMargins(12, 12, 12, 12)
    detail_layout.setSpacing(8)
    detail_layout.addLayout(header)
    detail_layout.addLayout(self._props_holder, stretch=1)

    split = QSplitter(Qt.Orientation.Horizontal)
    split.addWidget(self._tree)
    split.addWidget(detail)
    split.setStretchFactor(0, 3)
    split.setStretchFactor(1, 4)
    split.setSizes([360, 440])

    layout = QHBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(split)

  # ── tree ─────────────────────────────────────────────────────────

  def _build_tree(self, elements: List[Dict[str, Any]]) -> None:
    for element in elements:
      self._tree.addTopLevelItem(self._make_item(element))

  def _make_item(self, element: Dict[str, Any]) -> _ElementItem:
    item = _ElementItem(element)
    for child in element.get("sub_elements") or []:
      item.addChild(self._make_item(child))
    return item

  # ── selection ────────────────────────────────────────────────────

  def _on_select(self, current: Optional[QTreeWidgetItem], _prev) -> None:
    if not isinstance(current, _ElementItem):
      return
    element = current.element
    self._selected = element
    self._name.setText(_element_label(element))
    self._swap_props(self._element_properties(element))
    self._open_btn.setEnabled(self._resolve_spr(element) is not None)

  def _swap_props(self, widget: QWidget) -> None:
    self._props_holder.removeWidget(self._props)
    self._props.deleteLater()
    self._props = widget
    self._props_holder.addWidget(self._props)

  # ── property panels ──────────────────────────────────────────────

  def _file_properties(self) -> PropertiesView:
    rows = [
      ("Name", self._ctx.resource.name),
      ("Version", f"v.{self._version}"),
      ("Sprite sheet", self._file_spr or "—"),
    ]
    return PropertiesView([("Menu", rows)])

  def _element_properties(self, element: Dict[str, Any]) -> PropertiesView:
    rect = list(element.get("rectangle") or [0, 0, 0, 0])
    rect += [0] * (4 - len(rect))
    x1, y1, x2, y2 = rect[:4]
    layout_rows = [
      ("X", str(x1)),
      ("Y", str(y1)),
      ("Width", str(x2 - x1)),
      ("Height", str(y2 - y1)),
      ("Rectangle", f"({x1}, {y1}) → ({x2}, {y2})"),
    ]
    alpha = element.get("alpha")
    if isinstance(alpha, (list, tuple)):
      layout_rows.append(("Alpha", ", ".join(str(a) for a in alpha)))

    sprite_rows = [("Sprite index", str(element.get("spr_idx", 0)))]
    for label, key in _STATE_KEYS:
      if key in element:
        sprite_rows.append((label, str(element.get(key))))
    sprite_rows.append(("Sprite sheet", _spr_for(element, self._file_spr) or "—"))

    info_rows = [
      ("Label", _element_label(element)),
      ("Type", str(element.get("type") or "")),
      ("Sub-elements", str(len(element.get("sub_elements") or []))),
    ]
    sublabel = str(element.get("sublabel") or "").strip()
    if sublabel:
      info_rows.append(("Sub-label", sublabel))

    return PropertiesView(
      [("Element", info_rows), ("Layout", layout_rows), ("Sprites", sprite_rows)]
    )

  # ── open referenced sprite sheet ─────────────────────────────────

  def _resolve_spr(self, element: Optional[Dict[str, Any]]) -> Optional[Resource]:
    name = _spr_for(element, self._file_spr) if element else self._file_spr
    if not name:
      return None
    candidate = self._ctx.resource.sibling(name)
    return candidate if candidate.exists() else None

  def _open_spr(self) -> None:
    resource = self._resolve_spr(self._selected)
    if resource is not None:
      self._ctx.open_file(resource)
