from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTabBar, QTabWidget, QToolButton


class TabWidget(QTabWidget):
  """QTabWidget with inline add (+) and per-tab close (x) buttons.

  Qt's corner widget floats to the far edge, so the + is a child moved
  to sit right of the last tab (Chrome/VSCode). Close buttons are custom
  QToolButtons — reliable and styleable across platforms, unlike the
  built-in close button which a stylesheet can blank out.
  """

  add_clicked = Signal()

  def __init__(self, parent=None) -> None:
    super().__init__(parent)
    self.setMovable(True)
    self.setDocumentMode(True)
    self.setElideMode(Qt.TextElideMode.ElideRight)
    self._plus_allowed = True

    self._plus = QToolButton(self)
    self._plus.setObjectName("addTabButton")
    self._plus.setText("+")
    self._plus.setToolTip("Open a file in a new tab")
    self._plus.setCursor(Qt.CursorShape.PointingHandCursor)
    self._plus.setFixedSize(28, 28)
    self._plus.clicked.connect(self.add_clicked)

    self.currentChanged.connect(lambda _: self._reposition_plus())
    self.tabBar().tabMoved.connect(lambda *_: self._reposition_plus())

  # -- add-tab (+) button -----------------------------------------

  def set_plus_visible(self, visible: bool) -> None:
    self._plus_allowed = visible
    self._reposition_plus()

  def _reposition_plus(self) -> None:
    if not self._plus_allowed or self.count() == 0:
      self._plus.hide()
      return
    bar = self.tabBar()
    last = bar.tabRect(self.count() - 1)
    x = bar.x() + last.right() + 6
    y = bar.y() + (bar.height() - self._plus.height()) // 2
    x = min(x, self.width() - self._plus.width() - 4)
    self._plus.move(x, y)
    self._plus.show()
    self._plus.raise_()

  # -- per-tab close (x) button -----------------------------------

  _CLOSE_SIDE = QTabBar.ButtonPosition.RightSide

  def _update_close_buttons(self) -> None:
    """Give each tab a close (x) button unless the page opts out.

    A page marks itself non-closable with a falsy ``closable`` attribute
    (the welcome screen does); every other tab is closable even when
    it's the only one, so a lone content tab can be closed back to the
    welcome screen.
    """
    bar = self.tabBar()
    for index in range(self.count()):
      show = getattr(self.widget(index), "closable", True)
      existing = bar.tabButton(index, self._CLOSE_SIDE)
      if show and not isinstance(existing, QToolButton):
        self._install_close_button(index)
      elif not show and existing is not None:
        bar.setTabButton(index, self._CLOSE_SIDE, None)

  def _install_close_button(self, index: int) -> None:
    page = self.widget(index)
    button = QToolButton(self)
    button.setObjectName("tabCloseButton")
    button.setText("×")  # multiplication sign, in every UI font
    button.setToolTip("Close tab")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFixedSize(18, 18)
    button.clicked.connect(lambda: self._request_close(page))
    self.tabBar().setTabButton(index, self._CLOSE_SIDE, button)

  def _request_close(self, page) -> None:
    index = self.indexOf(page)
    if index >= 0:
      self.tabCloseRequested.emit(index)

  # -- QTabWidget overrides ---------------------------------------

  def resizeEvent(self, event) -> None:
    super().resizeEvent(event)
    self._reposition_plus()

  def tabInserted(self, index) -> None:
    super().tabInserted(index)
    self._update_close_buttons()
    self._reposition_plus()

  def tabRemoved(self, index) -> None:
    super().tabRemoved(index)
    self._update_close_buttons()
    self._reposition_plus()
