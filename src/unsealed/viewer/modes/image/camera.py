"""ImageCamera — orthographic 2D camera for the texture viewer."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from ...camera.base import Camera


class ImageCamera(Camera):
  """
  Orthographic 2D camera for the texture viewer.

  pan_x / pan_y : view-centre in world (pixel) units.
  zoom          : screen pixels per world pixel (higher = zoomed in).
  """

  def __init__(self) -> None:
    self.pan_x: float = 0.0
    self.pan_y: float = 0.0
    self.zoom: float = 1.0

  def update(self, dt: float) -> None:
    pass  # no spring needed

  def position(self) -> NDArray:
    return np.array([0.0, 0.0, 1.0], dtype=np.float32)

  def view_matrix(self) -> NDArray:
    return np.identity(4, dtype=np.float32)

  def projection_matrix(
    self, aspect: float, width: int = 0, height: int = 0
  ) -> NDArray:
    """Orthographic projection centred at (pan_x, pan_y) with current zoom."""
    if width <= 0 or height <= 0:
      return np.identity(4, dtype=np.float32)
    half_w = width / (2.0 * self.zoom)
    half_h = height / (2.0 * self.zoom)
    return self.ortho(
      self.pan_x - half_w,
      self.pan_x + half_w,
      self.pan_y - half_h,
      self.pan_y + half_h,
      -1.0,
      1.0,
    )

  def pan(self, dx: float, dy: float) -> None:
    """Pan by (dx, dy) screen pixels."""
    self.pan_x -= dx / self.zoom
    self.pan_y += dy / self.zoom  # screen y-down → world y-up

  def zoom_step(
    self, direction: int, mx: float, my: float, win_w: float, win_h: float
  ) -> None:
    """Zoom toward the screen coordinate (mx, my)."""
    # World position under the cursor before zoom
    wx = self.pan_x + (mx - win_w * 0.5) / self.zoom
    wy = self.pan_y + (win_h * 0.5 - my) / self.zoom

    factor = self.IMAGE_ZOOM_FACTOR if direction > 0 else 1.0 / self.IMAGE_ZOOM_FACTOR
    self.zoom = max(0.02, min(500.0, self.zoom * factor))

    # Keep the same world point under the cursor
    self.pan_x = wx - (mx - win_w * 0.5) / self.zoom
    self.pan_y = wy - (win_h * 0.5 - my) / self.zoom

  def fit_image(self, img_w: int, img_h: int, win_w: int, win_h: int) -> None:
    """Reset view so the image fits the viewport with a small margin."""
    self.pan_x = 0.0
    self.pan_y = 0.0
    if img_w > 0 and img_h > 0 and win_w > 0 and win_h > 0:
      self.zoom = min(win_w / img_w, win_h / img_h) * 0.92

  def reset(
    self, img_w: int = 0, img_h: int = 0, win_w: int = 0, win_h: int = 0
  ) -> None:
    self.fit_image(img_w, img_h, win_w, win_h)
