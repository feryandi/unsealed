"""A Windows-Properties-style key/value panel.

Generic and reusable: a title, then grouped sections of (key, value)
rows. Used for formats whose content is better summarised than walked
as a tree (e.g. an image `.tex`).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

Section = tuple[str, list[tuple[str, str]]]


class PropertiesView(QWidget):
  def __init__(self, sections: list[Section]) -> None:
    super().__init__()
    self.setObjectName("propertiesView")

    outer = QVBoxLayout(self)
    outer.setContentsMargins(24, 20, 24, 20)
    outer.setSpacing(0)

    for name, rows in sections:
      section = QLabel(name.upper())
      section.setObjectName("propSection")
      outer.addSpacing(18)
      outer.addWidget(section)
      outer.addSpacing(6)
      outer.addLayout(self._grid(rows))

    outer.addStretch(1)

  def _grid(self, rows: list[tuple[str, str]]) -> QGridLayout:
    grid = QGridLayout()
    grid.setColumnMinimumWidth(0, 130)
    grid.setColumnStretch(1, 1)
    grid.setHorizontalSpacing(18)
    grid.setVerticalSpacing(7)
    grid.setContentsMargins(0, 0, 0, 0)
    for i, (key, value) in enumerate(rows):
      key_label = QLabel(key)
      key_label.setObjectName("propKey")
      key_label.setAlignment(Qt.AlignmentFlag.AlignTop)
      value_label = QLabel(str(value))
      value_label.setObjectName("propValue")
      value_label.setWordWrap(True)
      value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
      grid.addWidget(key_label, i, 0)
      grid.addWidget(value_label, i, 1)
    return grid
