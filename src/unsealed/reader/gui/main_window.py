from pathlib import Path

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QFileDialog, QMainWindow

from ..vfs import Resource
from . import recent
from .tab_widget import TabWidget
from .tabs import ContentTab, WelcomeTab


class MainWindow(QMainWindow):
  """Browser-style tabbed shell.

  Starts with a single welcome tab (wordmark + Open + recents). Opening
  a file turns that tab into a content tab and reveals the inline
  add-tab (+) button; the + opens the system dialog for further tabs.
  Files can also be dragged anywhere onto the window.
  """

  def __init__(self, output_dir: Path | None = None) -> None:
    super().__init__()
    self.output_dir = output_dir
    self.setWindowTitle("Unsealed Reader")
    self.resize(1040, 720)
    self.setMinimumSize(760, 500)
    self.setAcceptDrops(True)

    self._tabs = TabWidget()
    self._tabs.tabCloseRequested.connect(self._close_tab)
    self._tabs.add_clicked.connect(self.action_new_tab)
    self.setCentralWidget(self._tabs)

    self._setup_shortcuts()
    self._show_welcome_tab()

  # -- shortcuts --------------------------------------------------

  def _setup_shortcuts(self) -> None:
    """Standard keys auto-map to Ctrl on Win/Linux and Cmd on macOS."""
    self._add_shortcut(QKeySequence.StandardKey.Open, self.action_open)
    self._add_shortcut(QKeySequence.StandardKey.AddTab, self.action_new_tab)
    # Ctrl+W (Cmd+W on macOS): StandardKey.Close is Ctrl+F4 on Windows.
    self._add_shortcut(QKeySequence("Ctrl+W"), self.action_close_tab)

  def _add_shortcut(self, key, slot) -> None:
    action = QAction(self)
    action.setShortcut(key)
    action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
    action.triggered.connect(slot)
    self.addAction(action)

  # -- commands ---------------------------------------------------

  def action_open(self) -> None:
    """Open a file, reusing the welcome tab or appending a new one."""
    path = self._prompt_for_file()
    if path is not None:
      self._open_path(path)

  def action_new_tab(self) -> None:
    """Open a file in a brand-new tab (+ button / Add-Tab shortcut)."""
    path = self._prompt_for_file()
    if path is not None:
      self._add_content_tab(Resource.for_disk_file(path), replace_current=False)

  def action_close_tab(self) -> None:
    index = self._tabs.currentIndex()
    if index >= 0:
      self._close_tab(index)

  def open_paths(self, paths: list[Path]) -> None:
    """Open each path; the first reuses the welcome tab (drag-drop)."""
    for path in paths:
      self._open_path(path)

  # -- tab lifecycle ----------------------------------------------

  def _show_welcome_tab(self) -> None:
    welcome = WelcomeTab(recent.load())
    welcome.open_requested.connect(self.action_open)
    welcome.recent_selected.connect(self._open_path)
    index = self._tabs.addTab(welcome, "New Tab")
    self._tabs.setCurrentIndex(index)
    self._update_add_button()

  def _open_path(self, path: Path) -> None:
    """Open a disk path, reusing the welcome tab if it's showing."""
    self._add_content_tab(
      Resource.for_disk_file(path), replace_current=self._current_is_welcome()
    )

  def open_in_new_tab(self, resource: Resource) -> None:
    """Open a related resource in a fresh tab.

    A map object / texture, or an entry inside a mounted `.spak`.
    """
    self._add_content_tab(resource, replace_current=False)

  def _add_content_tab(self, resource: Resource, *, replace_current: bool) -> None:
    disk = resource.disk_path
    if disk is not None:
      recent.add(disk)  # only real files are re-openable from recents
      tooltip = str(disk)
    else:  # archive entry: not a disk path, skip recents
      tooltip = resource.logical_name
    tab = ContentTab(resource, self.output_dir, open_file=self.open_in_new_tab)
    if replace_current:
      index = self._tabs.currentIndex()
      old = self._tabs.widget(index)
      self._tabs.removeTab(index)
      if old is not None:
        old.deleteLater()
      self._tabs.insertTab(index, tab, tab.title)
    else:
      index = self._tabs.addTab(tab, tab.title)
    self._tabs.setTabToolTip(index, tooltip)
    self._tabs.setCurrentIndex(index)
    self._update_add_button()

  def _close_tab(self, index: int) -> None:
    widget = self._tabs.widget(index)
    if widget is not None and not getattr(widget, "closable", True):
      return  # the welcome screen is the root state; nothing to close to
    self._tabs.removeTab(index)
    if widget is not None:
      widget.deleteLater()
    if self._tabs.count() == 0:
      self._show_welcome_tab()
    else:
      self._update_add_button()

  def _current_is_welcome(self) -> bool:
    return isinstance(self._tabs.currentWidget(), WelcomeTab)

  def _update_add_button(self) -> None:
    """Hide the + while the welcome tab is the only tab."""
    only_welcome = self._tabs.count() == 1 and isinstance(
      self._tabs.widget(0), WelcomeTab
    )
    self._tabs.set_plus_visible(not only_welcome)

  def _prompt_for_file(self) -> Path | None:
    filename, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*)")
    return Path(filename) if filename else None

  # -- drag and drop ----------------------------------------------

  def _paths_from_mime(self, mime: QMimeData) -> list[Path]:
    if not mime.hasUrls():
      return []
    paths = []
    for url in mime.urls():
      if url.isLocalFile():
        candidate = Path(url.toLocalFile())
        if candidate.is_file():
          paths.append(candidate)
    return paths

  def _set_drag_feedback(self, active: bool) -> None:
    current = self._tabs.currentWidget()
    if isinstance(current, WelcomeTab):
      current.set_drag_active(active)

  def dragEnterEvent(self, event) -> None:
    if self._paths_from_mime(event.mimeData()):
      event.acceptProposedAction()
      self._set_drag_feedback(True)

  def dragMoveEvent(self, event) -> None:
    if event.mimeData().hasUrls():
      event.acceptProposedAction()

  def dragLeaveEvent(self, event) -> None:
    self._set_drag_feedback(False)

  def dropEvent(self, event) -> None:
    self._set_drag_feedback(False)
    paths = self._paths_from_mime(event.mimeData())
    if paths:
      event.acceptProposedAction()
      self.open_paths(paths)
