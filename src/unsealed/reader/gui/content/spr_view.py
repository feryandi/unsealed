"""`.spr` sprite sheets -> an atlas/sprite tree with a properties panel.

A `.spr` is a list of referenced texture atlases, each carrying a set of
cropped sprite rectangles (quads) into that atlas. This view shows one
top-level node per atlas with its sprites beneath; selecting an atlas
shows its sprite count and lets you open the underlying texture
(`.tex`/`.te1`) in a new tab, while selecting a sprite shows its
rectangle (position + size) within the atlas.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import List, Optional, Tuple

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

# The decoder yields quads as (left, right, top, bottom).
Quad = Tuple[int, int, int, int]

# `ref_filename` may name a raw art file; the packed sibling is the
# encrypted .tex/.te1 with the same stem — prefer those (as the viewer).
_TEX_SUFFIXES: Tuple[str, ...] = (".tex", ".te1")


def _resolve_tex(base: Resource, ref_filename: str) -> Optional[Resource]:
  if not ref_filename:
    return None
  stem = PurePosixPath(ref_filename.replace("\\", "/")).stem
  for suffix in _TEX_SUFFIXES:
    candidate = base.sibling(f"{stem}{suffix}")
    if candidate.exists():
      return candidate
  literal = base.sibling(ref_filename)
  return literal if literal.exists() else None


class _AtlasItem(QTreeWidgetItem):
  """Top-level row for one referenced atlas file."""

  def __init__(self, filename: str, quads: List[Quad]) -> None:
    super().__init__()
    self.filename = filename
    self.quads = quads
    self.setText(0, PurePosixPath(filename.replace("\\", "/")).name or filename)
    self.setText(1, f"{len(quads)} sprite{'' if len(quads) == 1 else 's'}")


class _SpriteItem(QTreeWidgetItem):
  """Child row for one cropped sprite within an atlas."""

  def __init__(self, filename: str, index: int, quad: Quad) -> None:
    super().__init__()
    self.filename = filename
    self.index = index
    self.quad = quad
    left, right, top, bottom = quad
    self.setText(0, f"Sprite [{index}]")
    self.setText(1, f"{right - left} × {bottom - top}")


class SprView(QWidget):
  """Atlas/sprite tree (left) + properties / open-texture (right)."""

  def __init__(
    self, entries: List[Tuple[str, List[Quad]]], ctx: ContentContext
  ) -> None:
    super().__init__()
    self.setObjectName("sprView")
    self._ctx = ctx
    self._entries = entries
    self._current_atlas: Optional[str] = None

    self._tree = QTreeWidget()
    self._tree.setObjectName("assetTree")
    self._tree.setColumnCount(2)
    self._tree.setHeaderLabels(["Sprite", "Size"])
    self._tree.setUniformRowHeights(True)
    self._tree.setColumnWidth(0, 240)
    for filename, quads in entries:
      atlas = _AtlasItem(filename, quads)
      for i, quad in enumerate(quads):
        atlas.addChild(_SpriteItem(filename, i, quad))
      self._tree.addTopLevelItem(atlas)
    self._tree.currentItemChanged.connect(self._on_select)

    self._name = QLabel("Select a sprite")
    self._name.setObjectName("mapDetailName")
    self._open_btn = QPushButton("Open texture")
    self._open_btn.setObjectName("mapOpenButton")
    self._open_btn.setEnabled(False)
    self._open_btn.clicked.connect(self._open_tex)
    header = QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)
    header.addWidget(self._name)
    header.addStretch(1)
    header.addWidget(self._open_btn)

    self._props_holder = QVBoxLayout()
    self._props_holder.setContentsMargins(0, 0, 0, 0)
    self._props: QWidget = self._summary_properties()
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

  # ── selection ────────────────────────────────────────────────────

  def _on_select(self, current: Optional[QTreeWidgetItem], _prev) -> None:
    if isinstance(current, _AtlasItem):
      self._current_atlas = current.filename
      self._name.setText(current.text(0))
      self._swap_props(self._atlas_properties(current))
    elif isinstance(current, _SpriteItem):
      self._current_atlas = current.filename
      self._name.setText(current.text(0))
      self._swap_props(self._sprite_properties(current))
    else:
      return
    self._open_btn.setEnabled(
      _resolve_tex(self._ctx.resource, self._current_atlas or "") is not None
    )

  def _swap_props(self, widget: QWidget) -> None:
    self._props_holder.removeWidget(self._props)
    self._props.deleteLater()
    self._props = widget
    self._props_holder.addWidget(self._props)

  # ── property panels ──────────────────────────────────────────────

  def _summary_properties(self) -> PropertiesView:
    total_sprites = sum(len(quads) for _, quads in self._entries)
    rows = [
      ("Name", self._ctx.resource.name),
      ("Atlases", str(len(self._entries))),
      ("Sprites", str(total_sprites)),
    ]
    return PropertiesView([("Sprite Sheet", rows)])

  def _atlas_properties(self, item: _AtlasItem) -> PropertiesView:
    tex = _resolve_tex(self._ctx.resource, item.filename)
    rows = [
      ("Reference", item.filename),
      ("Sprites", str(len(item.quads))),
      ("Texture", tex.name if tex is not None else "not found"),
    ]
    return PropertiesView([("Atlas", rows)])

  def _sprite_properties(self, item: _SpriteItem) -> PropertiesView:
    left, right, top, bottom = item.quad
    rows = [
      ("Index", str(item.index)),
      ("X", str(left)),
      ("Y", str(top)),
      ("Width", str(right - left)),
      ("Height", str(bottom - top)),
      ("Rectangle", f"({left}, {top}) → ({right}, {bottom})"),
    ]
    atlas_rows = [
      ("Reference", item.filename),
      ("Texture", PurePosixPath(item.filename.replace("\\", "/")).name),
    ]
    return PropertiesView([("Sprite", rows), ("Atlas", atlas_rows)])

  # ── open referenced texture ──────────────────────────────────────

  def _open_tex(self) -> None:
    if not self._current_atlas:
      return
    resource = _resolve_tex(self._ctx.resource, self._current_atlas)
    if resource is not None:
      self._ctx.open_file(resource)
