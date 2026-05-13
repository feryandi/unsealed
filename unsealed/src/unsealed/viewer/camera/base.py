"""
Base Camera class: shared constants and matrix / bounds utilities.

All matrix functions return row-major float32 numpy arrays (standard convention
throughout the renderer — matrices are uploaded with GL_TRUE transpose flag).
"""

from __future__ import annotations

from abc import ABC
import math
from typing import Tuple

import numpy as np
from numpy.typing import NDArray


class Camera(ABC):
  """Base camera; provides shared constants and static matrix / bounds helpers."""

  # How quickly smooth-zoom snaps to the target (higher = snappier, ~100 ms at 14).
  ZOOM_SPRING: float = 14.0
  # Fraction of current distance removed per scroll tick.
  ZOOM_STEP: float = 0.12
  # Mouse-drag sensitivity in degrees per pixel (orbit cameras).
  ORBIT_SENS: float = 0.30
  # Pan sensitivity for OrbitCamera (world units per pixel per unit distance).
  PAN_SENS: float = 0.0015
  # Grab-drag scale for MapCamera MMB pan.
  MAP_PAN_SENS: float = 0.003
  # Per-tick zoom factor for ImageCamera scroll.
  IMAGE_ZOOM_FACTOR: float = 1.15

  def position(self) -> NDArray:
    """Return the camera's world-space position as a (3,) float32 array."""
    raise NotImplementedError

  # ── matrix helpers ───────────────────────────────────────────────────────

  @staticmethod
  def look_at(eye: NDArray, center: NDArray, up: NDArray) -> NDArray:
    """Build a view matrix from eye position, look-at point and world up."""
    f = center - eye
    f_len = float(np.linalg.norm(f))
    if f_len < 1e-10:
      return np.identity(4, dtype=np.float32)
    f = f / f_len

    r = np.cross(f, up)
    r_len = float(np.linalg.norm(r))
    r = r / r_len if r_len > 1e-10 else np.array([1.0, 0.0, 0.0], dtype=np.float32)
    u = np.cross(r, f)

    m = np.identity(4, dtype=np.float32)
    m[0, :3] = r
    m[1, :3] = u
    m[2, :3] = -f
    m[0, 3] = -float(np.dot(r, eye))
    m[1, 3] = -float(np.dot(u, eye))
    m[2, 3] = float(np.dot(f, eye))
    return m

  @staticmethod
  def perspective(fov_deg: float, aspect: float, near: float, far: float) -> NDArray:
    """Standard symmetric perspective projection matrix."""
    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2.0 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m

  @staticmethod
  def ortho(
    left: float, right: float, bottom: float, top: float, near: float, far: float
  ) -> NDArray:
    """Standard column-major orthographic projection matrix (row-major numpy storage)."""
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = 2.0 / (right - left)
    m[1, 1] = 2.0 / (top - bottom)
    m[2, 2] = -2.0 / (far - near)
    m[0, 3] = -(right + left) / (right - left)
    m[1, 3] = -(top + bottom) / (top - bottom)
    m[2, 3] = -(far + near) / (far - near)
    m[3, 3] = 1.0
    return m

  @staticmethod
  def compute_bounds(positions: NDArray) -> Tuple[NDArray, float]:
    """Return (center, radius) bounding sphere for a set of 3D positions."""
    if len(positions) == 0:
      return np.zeros(3, dtype=np.float32), 1.0
    center = (positions.min(axis=0) + positions.max(axis=0)) * 0.5
    radius = float(np.linalg.norm(positions - center, axis=1).max())
    return center.astype(np.float32), max(radius, 0.01)
