"""A preview canvas beside a Windows-Properties-style panel for images.

Shared by the `.tex`/`.te1` handler and the standard-image handler
(`.png`/`.jpg`/`.dds`/…). The left canvas paints the decoded pixels on a
checkerboard (so alpha is visible), scaling large images down to fit
but never upscaling past native size; the right reuses `PropertiesView`.

Also hosts the file/size helpers those handlers share, so a location and
byte count read the same whether the file is loose on disk or an entry
inside a mounted archive.
"""

from __future__ import annotations

from typing import Optional

from PIL import Image
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
  QHBoxLayout,
  QScrollArea,
  QSplitter,
  QWidget,
)

from ...vfs import Resource
from .properties import PropertiesView, Section

# Checkerboard shades used behind (semi-)transparent images.
_CHECK_A = QColor("#1B1E24")
_CHECK_B = QColor("#22262E")
_CHECK_SIZE = 12


def human_size(n: int) -> str:
  size = float(n)
  for unit in ("B", "KB", "MB", "GB"):
    if size < 1024 or unit == "GB":
      return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
    size /= 1024
  return f"{n} B"


def size_row(n: int) -> str:
  return f"{human_size(n)} ({n:,} bytes)"


def file_meta(resource: Resource) -> tuple[str, int]:
  """(location, byte size) for a disk file or an archive entry."""
  disk = resource.disk_path
  if disk is not None:
    return str(disk.parent), disk.stat().st_size
  archive = getattr(resource.source, "path", None)
  location = f"{archive.name} (archive)" if archive is not None else "archive"
  try:
    return location, len(resource.read())
  except Exception:
    return location, 0


def pil_to_pixmap(image: Image.Image) -> QPixmap:
  """Convert a PIL image to a QPixmap via a detached RGBA QImage."""
  if image.mode != "RGBA":
    image = image.convert("RGBA")
  data = image.tobytes("raw", "RGBA")
  qimage = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888)
  # Copy so the pixmap owns its pixels (the `data` buffer is transient).
  return QPixmap.fromImage(qimage.copy())


class _ImageCanvas(QWidget):
  """Paints a pixmap centered on a checkerboard, downscaled to fit."""

  def __init__(self, pixmap: Optional[QPixmap]) -> None:
    super().__init__()
    self.setObjectName("imageCanvas")
    self._pixmap = pixmap
    self.setMinimumSize(160, 160)

  def paintEvent(self, _event) -> None:
    painter = QPainter(self)
    rect = self.rect()
    self._paint_checker(painter, rect)
    if self._pixmap is None or self._pixmap.isNull():
      return
    size = self._pixmap.size()
    # Downscale to fit; keep native size for images that already fit so
    # small sprites/textures aren't blurred by upscaling.
    if size.width() > rect.width() or size.height() > rect.height():
      size = size.scaled(rect.size(), Qt.AspectRatioMode.KeepAspectRatio)
    x = rect.x() + (rect.width() - size.width()) // 2
    y = rect.y() + (rect.height() - size.height()) // 2
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.drawPixmap(QRect(QPoint(x, y), size), self._pixmap)

  @staticmethod
  def _paint_checker(painter: QPainter, rect: QRect) -> None:
    painter.fillRect(rect, _CHECK_A)
    for y in range(rect.top(), rect.bottom() + 1, _CHECK_SIZE):
      for x in range(rect.left(), rect.right() + 1, _CHECK_SIZE):
        if ((x // _CHECK_SIZE) + (y // _CHECK_SIZE)) % 2 == 0:
          painter.fillRect(x, y, _CHECK_SIZE, _CHECK_SIZE, _CHECK_B)


class ImageView(QWidget):
  """Preview canvas (left) + properties panel (right)."""

  def __init__(self, pixmap: Optional[QPixmap], sections: list[Section]) -> None:
    super().__init__()
    self.setObjectName("imageView")

    canvas = _ImageCanvas(pixmap)

    props = QScrollArea()
    props.setObjectName("imageProps")
    props.setWidgetResizable(True)
    props.setWidget(PropertiesView(sections))

    split = QSplitter(Qt.Orientation.Horizontal)
    split.addWidget(canvas)
    split.addWidget(props)
    split.setStretchFactor(0, 3)
    split.setStretchFactor(1, 2)
    split.setSizes([560, 320])

    layout = QHBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(split)
