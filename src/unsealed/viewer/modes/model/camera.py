"""OrbitCamera — WoW-style 3D orbit camera for the mesh / actor viewer."""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from ...camera.base import Camera


class OrbitCamera(Camera):
  """
  WoW-style orbit camera.

  - orbit()  : direct (no lag), maps to left-drag and right-drag
  - zoom()   : sets a target distance; call update(dt) each frame to smooth it
  - pan()    : shifts the look-at target in the camera's local XY plane
  - update() : call once per frame to advance the smooth-zoom spring
  """

  def __init__(self) -> None:
    self.theta: float = 45.0  # azimuth, degrees
    self.phi: float = 25.0  # elevation, degrees
    self.distance: float = 10.0
    self._dist_target: float = 10.0  # smooth-zoom target
    self.target: NDArray = np.zeros(3, dtype=np.float32)
    self.fov: float = 45.0
    self.near: float = 0.01
    self.far: float = 100_000.0

  # ── called every frame ────────────────────────────────────────────────────

  def update(self, dt: float) -> None:
    """Advance the smooth-zoom spring. dt is seconds since last frame."""
    alpha = min(1.0, self.ZOOM_SPRING * dt)
    self.distance += (self._dist_target - self.distance) * alpha

  # ── matrices ─────────────────────────────────────────────────────────────

  def position(self) -> NDArray:
    t = math.radians(self.theta)
    p = math.radians(self.phi)
    x = self.distance * math.cos(p) * math.sin(t)
    y = self.distance * math.sin(p)
    z = self.distance * math.cos(p) * math.cos(t)
    return self.target + np.array([x, y, z], dtype=np.float32)

  def view_matrix(self) -> NDArray:
    return self.look_at(
      self.position(),
      self.target,
      np.array([0.0, 1.0, 0.0], dtype=np.float32),
    )

  def projection_matrix(
    self, aspect: float, width: int = 0, height: int = 0
  ) -> NDArray:
    return self.perspective(self.fov, aspect, self.near, self.far)

  # ── input handlers ────────────────────────────────────────────────────────

  def orbit(self, dx: float, dy: float) -> None:
    """Rotate around the target. dx = horizontal pixels, dy = vertical pixels."""
    self.theta += dx * self.ORBIT_SENS
    self.phi = max(-89.0, min(89.0, self.phi + dy * self.ORBIT_SENS))

  def pan(self, dx: float, dy: float) -> None:
    """Slide the look-at target in camera space. dx/dy in pixels."""
    t = math.radians(self.theta)
    right = np.array([math.cos(t), 0.0, -math.sin(t)], dtype=np.float32)
    up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    scale = self.distance * self.PAN_SENS
    self.target -= right * dx * scale
    self.target += up * dy * scale

  def zoom(self, direction: int) -> None:
    """
    Queue a zoom step.  direction > 0 zooms in, < 0 zooms out.
    Step size is proportional to current target distance (feel-proportional).
    """
    step = self._dist_target * self.ZOOM_STEP
    self._dist_target -= direction * step
    self._dist_target = max(0.001, min(1_000_000.0, self._dist_target))

  # ── utility ───────────────────────────────────────────────────────────────

  def fit_bounds(self, center: NDArray, radius: float) -> None:
    self.target = center.copy().astype(np.float32)
    self.distance = radius * 2.8
    self._dist_target = self.distance
    self.near = max(radius * 0.001, 0.001)
    self.far = radius * 200.0

  def reset(self) -> None:
    self.theta = 45.0
    self.phi = 25.0
    self.distance = 10.0
    self._dist_target = 10.0
    self.target = np.zeros(3, dtype=np.float32)
