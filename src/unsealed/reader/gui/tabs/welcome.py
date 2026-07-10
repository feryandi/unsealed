from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
  QFrame,
  QHBoxLayout,
  QLabel,
  QPushButton,
  QVBoxLayout,
  QWidget,
)

from ..fonts import MONO_FAMILIES, UI_FAMILIES
from ..style import ACCENT


class RecentRow(QFrame):
  """One clickable recent-file entry: name plus its folder."""

  clicked = Signal(Path)

  def __init__(self, path: Path) -> None:
    super().__init__()
    self._path = path
    self.setObjectName("recentRow")
    self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    self.setCursor(Qt.CursorShape.PointingHandCursor)
    self.setToolTip(str(path))

    name = QLabel(path.name)
    name.setObjectName("recentName")
    folder = QLabel(str(path.parent))
    folder.setObjectName("recentPath")

    row = QHBoxLayout(self)
    row.setContentsMargins(12, 7, 12, 7)
    row.setSpacing(14)
    row.addWidget(name)
    row.addStretch(1)
    row.addWidget(folder)

  def mouseReleaseEvent(self, event) -> None:
    if event.button() == Qt.MouseButton.LeftButton:
      self.clicked.emit(self._path)


class WelcomeTab(QWidget):
  """New-tab start screen: wordmark, Open action, drag hint, recents."""

  # The welcome screen is the app's root state, so it has no close (x)
  # button — closing the last content tab returns here instead.
  closable = False

  open_requested = Signal()
  recent_selected = Signal(Path)

  def __init__(self, recents: list[Path] | None = None) -> None:
    super().__init__()
    self.setObjectName("welcomeTab")

    self._column = QWidget()
    self._column.setObjectName("welcomeColumn")
    self._column.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    self._column.setFixedWidth(520)

    col = QVBoxLayout(self._column)
    col.setContentsMargins(28, 28, 28, 28)
    col.setSpacing(0)

    col.addWidget(self._build_wordmark())
    col.addSpacing(6)
    subtitle = QLabel("Decode Seal Online game files")
    subtitle.setObjectName("subtitle")
    col.addWidget(subtitle)

    col.addSpacing(26)
    open_btn = QPushButton("Open File…")
    open_btn.setObjectName("openButton")
    open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    open_btn.clicked.connect(self.open_requested)
    open_row = QHBoxLayout()
    open_row.setContentsMargins(0, 0, 0, 0)
    open_row.addWidget(open_btn)
    open_row.addStretch(1)
    col.addLayout(open_row)

    col.addSpacing(10)
    hint = QLabel("or drag a file anywhere to open")
    hint.setObjectName("dropHint")
    col.addWidget(hint)

    col.addSpacing(34)
    col.addWidget(self._build_recents(recents or []))

    outer = QVBoxLayout(self)
    outer.addStretch(1)
    outer.addWidget(self._column, alignment=Qt.AlignmentFlag.AlignHCenter)
    outer.addStretch(1)

  def _build_wordmark(self) -> QLabel:
    label = QLabel(f'unsealed<span style="color:{ACCENT}">▌</span>')
    label.setObjectName("wordmark")
    label.setTextFormat(Qt.TextFormat.RichText)
    font = QFont()
    font.setFamilies(MONO_FAMILIES)
    font.setPixelSize(46)
    font.setWeight(QFont.Weight.DemiBold)
    label.setFont(font)
    return label

  def _build_recents(self, recents: list[Path]) -> QWidget:
    box = QFrame()
    box.setObjectName("recentBox")
    lay = QVBoxLayout(box)
    lay.setContentsMargins(8, 8, 8, 8)
    lay.setSpacing(2)

    eyebrow = QLabel("RECENT")
    eyebrow.setObjectName("recentEyebrow")
    efont = QFont()
    efont.setFamilies(UI_FAMILIES)
    efont.setPixelSize(11)
    efont.setWeight(QFont.Weight.DemiBold)
    efont.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
    eyebrow.setFont(efont)
    eyebrow.setContentsMargins(4, 2, 4, 4)
    lay.addWidget(eyebrow)

    if not recents:
      empty = QLabel("No recent files yet. Open one to get started.")
      empty.setObjectName("recentEmpty")
      empty.setContentsMargins(4, 2, 4, 4)
      lay.addWidget(empty)
      return box

    for path in recents:
      row = RecentRow(path)
      row.clicked.connect(self.recent_selected)
      lay.addWidget(row)
    return box

  def set_drag_active(self, active: bool) -> None:
    """Highlight the drop target while a file is dragged over."""
    self._column.setProperty("dragActive", active)
    self._column.style().unpolish(self._column)
    self._column.style().polish(self._column)
