"""`.spak` archives -> an in-app browser over the mounted archive.

Opening a `.spak` mounts it (reading the file list without decrypting),
then lists its entries; clicking one decrypts just that entry and opens
it in a new tab. Mounting runs on a worker thread because resolving a
private-server key (and any client-dump scan) can be slow -- the UI
shows progress instead of freezing, and a private archive with no known
key lands on a graceful "needs key" panel rather than a raw traceback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Set

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
  QAbstractItemView,
  QApplication,
  QHBoxLayout,
  QHeaderView,
  QLabel,
  QLineEdit,
  QPushButton,
  QStackedWidget,
  QTableWidget,
  QTableWidgetItem,
  QVBoxLayout,
  QWidget,
)

from ...assets import spak_keystore
from ...assets.spak import SpakPasswordError
from ...utils import spak_recover
from ...vfs import Resource
from ...vfs.spak_source import SpakSource
from .registry import ContentContext

# Strong refs to running workers so they aren't GC'd mid-run even if
# their view is closed (Qt auto-disconnects the dead view's slots, so a
# late signal from an orphaned worker is simply dropped).
_LIVE_WORKERS: Set[QThread] = set()
_drain_hooked = False


def _drain_on_quit() -> None:
  """Let in-flight mounts/scans finish so no QThread is destroyed while
  still running (which would abort at shutdown)."""
  for worker in list(_LIVE_WORKERS):
    worker.wait(3000)


def _track(worker: QThread) -> None:
  global _drain_hooked
  _LIVE_WORKERS.add(worker)
  worker.finished.connect(lambda: _LIVE_WORKERS.discard(worker))
  if not _drain_hooked:  # once, now that a QApplication surely exists
    app = QApplication.instance()
    if app is not None:
      app.aboutToQuit.connect(_drain_on_quit)
      _drain_hooked = True
  worker.start()


def _human_size(n: int) -> str:
  size = float(n)
  for unit in ("B", "KB", "MB", "GB"):
    if size < 1024 or unit == "GB":
      return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
    size /= 1024
  return f"{n} B"


def _fmt_mtime(dt: Optional[tuple]) -> str:
  """Zip date_time (Y, M, D, h, m, s) -> sortable 'YYYY-MM-DD HH:MM'."""
  if not dt or len(dt) < 5 or dt[0] < 1980:
    return "—"
  return f"{dt[0]:04d}-{dt[1]:02d}-{dt[2]:02d} {dt[3]:02d}:{dt[4]:02d}"


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


class _MountWorker(QThread):
  """Mount a .spak off the UI thread (key resolution can be slow)."""

  status = Signal(str)
  mounted = Signal(object)  # SpakSource
  needs_key = Signal(object)  # SpakPasswordError
  failed = Signal(str)

  def __init__(self, path: Path) -> None:
    super().__init__()
    self._path = path

  def run(self) -> None:
    try:
      source = SpakSource(self._path, on_status=self.status.emit)
    except SpakPasswordError as e:
      self.needs_key.emit(e)
    except Exception as e:  # surfaced in the UI, not a crash
      self.failed.emit(str(e))
    else:
      self.mounted.emit(source)


class _RecoverWorker(QThread):
  """Recover a private-server key (scan dumps, else launch+dump)."""

  status = Signal(str)
  recovered = Signal()  # key found + saved to the store -> re-mount
  none_found = Signal()  # scanned, nothing matched
  admin_needed = Signal(str)
  failed = Signal(str)

  def __init__(self, path: Path) -> None:
    super().__init__()
    self._path = path

  def run(self) -> None:
    try:
      install = self._path.resolve().parent.parent
      verify = spak_recover.make_verifier(self._path)
      key = spak_recover.recover_key(install, verify, on_status=self.status.emit)
    except spak_recover.RecoveryNeedsAdmin as e:
      self.admin_needed.emit(str(e))
    except Exception as e:
      self.failed.emit(str(e))
    else:
      if key is None:
        self.none_found.emit()
      else:
        spak_keystore.save_key(key, label=install.name)
        self.recovered.emit()


class SpakView(QWidget):
  """Loading -> browser / key panel / error, over one .spak."""

  def __init__(self, path: Path, ctx: ContentContext) -> None:
    super().__init__()
    self.setObjectName("spakView")
    self._path = Path(path)
    self._ctx = ctx
    # Kept alive so entry Resources opened from it stay valid after the
    # browser tab itself is closed.
    self._source: Optional[SpakSource] = None
    self._mount: Optional[_MountWorker] = None
    self._recover: Optional[_RecoverWorker] = None

    self._stack = QStackedWidget()
    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(self._stack)

    self._build_loading()
    self._build_browser()
    self._build_keypanel()
    self._build_error()

    self._start_mount()

  # ── pages ──────────────────────────────────────────────────────

  def _build_loading(self) -> None:
    page = QWidget()
    box = QVBoxLayout(page)
    box.setContentsMargins(24, 24, 24, 24)
    box.addStretch(1)
    title = QLabel(f"Opening {self._path.name}…")
    title.setObjectName("spakLoadingTitle")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self._loading_status = QLabel("Reading archive")
    self._loading_status.setObjectName("spakStatus")
    self._loading_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
    box.addWidget(title)
    box.addWidget(self._loading_status)
    box.addStretch(1)
    self._page_loading = self._stack.addWidget(page)

  def _build_browser(self) -> None:
    page = QWidget()
    box = QVBoxLayout(page)
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

    self._table = QTableWidget(0, 3)
    self._table.setObjectName("spakTable")
    self._table.setHorizontalHeaderLabels(["Name", "Size", "Modified"])
    self._table.verticalHeader().setVisible(False)
    self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    self._table.setShowGrid(False)
    self._table.setSortingEnabled(True)
    head = self._table.horizontalHeader()
    head.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    head.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    head.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    self._table.itemActivated.connect(self._open_item)  # double-click / Enter

    hint = QLabel("Double-click a file to open it in a new tab.")
    hint.setObjectName("spakStatus")

    box.addLayout(bar)
    box.addWidget(self._table, stretch=1)
    box.addWidget(hint)
    self._page_browser = self._stack.addWidget(page)

  def _build_keypanel(self) -> None:
    page = QWidget()
    box = QVBoxLayout(page)
    box.setContentsMargins(24, 24, 24, 24)
    box.setSpacing(10)
    box.addStretch(1)

    heading = QLabel("This archive needs a decryption key")
    heading.setObjectName("keyHeading")
    self._key_body = QLabel()
    self._key_body.setObjectName("keyBody")
    self._key_body.setWordWrap(True)
    guide = QLabel(
      "Private-server archives are repacked with a fixed password that "
      "can't be derived. Unsealed can recover it from the game client's "
      "memory — this may need administrator rights. Once recovered the key "
      "is saved locally and every archive from that server opens "
      "automatically."
    )
    guide.setObjectName("keyGuide")
    guide.setWordWrap(True)

    buttons = QHBoxLayout()
    buttons.setContentsMargins(0, 0, 0, 0)
    self._recover_btn = QPushButton("Recover key")
    self._recover_btn.setObjectName("mapOpenButton")
    self._recover_btn.clicked.connect(self._start_recover)
    self._retry_btn = QPushButton("Retry")
    self._retry_btn.setObjectName("mapOpenButton")
    self._retry_btn.clicked.connect(self._start_mount)
    buttons.addWidget(self._recover_btn)
    buttons.addWidget(self._retry_btn)
    buttons.addStretch(1)

    self._key_status = QLabel("")
    self._key_status.setObjectName("keyStatus")
    self._key_status.setWordWrap(True)

    box.addWidget(heading)
    box.addWidget(self._key_body)
    box.addWidget(guide)
    box.addLayout(buttons)
    box.addWidget(self._key_status)
    box.addStretch(2)
    self._page_key = self._stack.addWidget(page)

  def _build_error(self) -> None:
    page = QWidget()
    box = QVBoxLayout(page)
    box.setContentsMargins(24, 24, 24, 24)
    box.addStretch(1)
    heading = QLabel("Couldn't open this archive")
    heading.setObjectName("errorHeading")
    self._error_body = QLabel()
    self._error_body.setObjectName("keyBody")
    self._error_body.setWordWrap(True)
    box.addWidget(heading)
    box.addWidget(self._error_body)
    box.addStretch(2)
    self._page_error = self._stack.addWidget(page)

  # ── mount ──────────────────────────────────────────────────────

  def _start_mount(self) -> None:
    self._loading_status.setText("Reading archive")
    self._stack.setCurrentIndex(self._page_loading)
    self._mount = _MountWorker(self._path)
    self._mount.status.connect(self._loading_status.setText)
    self._mount.mounted.connect(self._on_mounted)
    self._mount.needs_key.connect(self._on_needs_key)
    self._mount.failed.connect(self._on_failed)
    _track(self._mount)

  def _on_mounted(self, source: SpakSource) -> None:
    self._source = source
    entries = source.primary_entries()
    # Populate with sorting off, then restore (Qt re-sorts inserts).
    self._table.setSortingEnabled(False)
    self._table.setRowCount(0)
    for entry in entries:
      row = self._table.rowCount()
      self._table.insertRow(row)
      name_item = QTableWidgetItem(entry.name)
      name_item.setData(Qt.ItemDataRole.UserRole, entry.name)
      self._table.setItem(row, 0, name_item)
      self._table.setItem(row, 1, _SizeItem(entry.size))
      self._table.setItem(row, 2, QTableWidgetItem(_fmt_mtime(entry.mtime)))
    self._table.setSortingEnabled(True)
    self._table.sortItems(0, Qt.SortOrder.AscendingOrder)
    n = len(entries)
    self._count.setText(f"{n:,} file{'' if n == 1 else 's'}")
    self._stack.setCurrentIndex(self._page_browser)

  def _on_needs_key(self, err: SpakPasswordError) -> None:
    self._key_body.setText(str(err))
    self._key_status.setText("")
    self._recover_btn.setEnabled(True)
    self._retry_btn.setEnabled(True)
    self._stack.setCurrentIndex(self._page_key)

  def _on_failed(self, message: str) -> None:
    self._error_body.setText(message)
    self._stack.setCurrentIndex(self._page_error)

  # ── browsing ───────────────────────────────────────────────────

  def _filter(self, text: str) -> None:
    needle = text.strip().lower()
    for row in range(self._table.rowCount()):
      name = self._table.item(row, 0).text().lower()
      self._table.setRowHidden(row, bool(needle) and needle not in name)

  def _open_item(self, item) -> None:
    if self._source is None:
      return
    name = self._table.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
    self._ctx.open_file(Resource(self._source, name))

  # ── key recovery ───────────────────────────────────────────────

  def _start_recover(self) -> None:
    self._recover_btn.setEnabled(False)
    self._retry_btn.setEnabled(False)
    self._key_status.setText("Starting recovery…")
    self._recover = _RecoverWorker(self._path)
    self._recover.status.connect(self._key_status.setText)
    self._recover.recovered.connect(self._on_recovered)
    self._recover.none_found.connect(self._on_none_found)
    self._recover.admin_needed.connect(self._on_admin_needed)
    self._recover.failed.connect(self._on_recover_failed)
    _track(self._recover)

  def _on_recovered(self) -> None:
    # Key is in the store now; re-mount to decrypt and list the entries.
    self._start_mount()

  def _on_none_found(self) -> None:
    self._recover_btn.setEnabled(True)
    self._retry_btn.setEnabled(True)
    self._key_status.setText(
      "No key found. Launch the game client to its login screen so it "
      "unpacks in memory, then press Recover key again."
    )

  def _on_admin_needed(self, _message: str) -> None:
    self._recover_btn.setEnabled(True)
    self._retry_btn.setEnabled(True)
    self._key_status.setText(
      "Automatic recovery needs administrator rights. Close Unsealed Reader "
      "and reopen it as administrator (right-click the app → Run as "
      "administrator), then press Recover key again — or run "
      "'unsealed-reader recover-key' in an elevated terminal."
    )

  def _on_recover_failed(self, message: str) -> None:
    self._recover_btn.setEnabled(True)
    self._retry_btn.setEnabled(True)
    self._key_status.setText(f"Recovery failed: {message}")
