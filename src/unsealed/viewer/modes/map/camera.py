"""MapCamera — RTS-style open-world camera for the map viewer."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from ...camera.base import Camera


class MapCamera(Camera):
  """
  RTS-style open-world camera for the map viewer.

  - LMB drag              : pan target in XZ.
  - RMB drag              : rotate (azimuth + pitch).
  - MMB drag              : pan target in XZ (grab-drag).
  - Scroll wheel          : zoom (adjust camera height, smooth spring).
  - R / F                 : reset to fit the map.
  """

  EDGE_SPEED    = 300.0  # world units / second for key pan (at height 300)
  MIN_CLEARANCE = 8.0    # minimum world units above terrain surface

  def __init__(self) -> None:
    self.target: NDArray  = np.array([256.0, 0.0, 256.0], dtype=np.float32)
    self.theta: float     = 0.0    # azimuth, degrees
    self.pitch: float     = 55.0   # elevation above horizontal, degrees [20, 89]
    self.height: float    = 400.0  # camera Y above world origin
    self._h_target: float = 400.0  # smooth-zoom target height
    self.fov: float       = 45.0
    self.near: float      = 1.0
    self.far: float       = 10_000.0
    # Optional heightmap for terrain-floor clamping
    self._heights: Optional[NDArray] = None   # (H, W) float32
    self._map_w:   int = 512
    self._map_h:   int = 512

  # ── heightmap helpers ──────────────────────────────────────────────────────

  def set_heightmap(self, heights: NDArray, map_w: int = 512, map_h: int = 512) -> None:
    """Provide the terrain height grid so zoom can clamp above the surface."""
    self._heights = heights
    self._map_w   = map_w
    self._map_h   = map_h

  def _terrain_h_at(self, wx: float, wz: float) -> float:
    if self._heights is None:
      return 0.0
    xi = int(np.clip(wx, 0, self._map_w - 1))
    zi = int(np.clip(wz, 0, self._map_h - 1))
    return float(self._heights[zi, xi])

  def _raycast_center(self) -> Optional[NDArray]:
    """Ray-march from camera along the look-at direction to find the terrain hit.
    Returns world-space hit point or None if no heightmap / no intersection."""
    if self._heights is None:
      return None
    pos  = self.position().astype(np.float64)
    tgt  = self.target.astype(np.float64)
    fwd  = tgt - pos
    dist = float(np.linalg.norm(fwd))
    if dist < 1e-6:
      return None
    fwd = (fwd / dist).astype(np.float32)
    step = max(1.0, dist / 400.0)
    p = pos.astype(np.float32)
    for _ in range(600):
      p  = p + fwd * step
      th = self._terrain_h_at(p[0], p[2])
      if p[1] <= th:
        return np.array([p[0], th, p[2]], dtype=np.float32)
    return None

  def raycast_terrain_screen(
    self,
    mx: int,
    my: int,
    win_w: int,
    win_h: int,
  ) -> Optional[NDArray]:
    """Ray-march from a screen pixel against the heightmap surface.

    Reconstructs a world-space ray for the pixel via the camera's current
    view/projection (the renderer's _mirror_x is NOT applied — we work in
    plain world space here), then steps along it until the ray's Y dips
    below the local terrain height. Returns the world-space hit point or
    None if the ray never lands on terrain.
    """
    if self._heights is None or win_w <= 0 or win_h <= 0:
      return None

    aspect = win_w / max(win_h, 1)
    view = self.view_matrix()
    proj = self.projection_matrix(aspect, win_w, win_h)
    # Renderer mirrors X before drawing; match that here so the unprojected
    # ray lines up with what the user actually sees on screen.
    mirror_x = np.diag(np.array([-1.0, 1.0, 1.0, 1.0], dtype=np.float32))
    proj = mirror_x @ proj

    # Reuse the renderer's unproject helper so the math stays in one place.
    from ...rendering.math_utils import unproject_ray

    origin, direction = unproject_ray(mx, my, win_w, win_h, view, proj)
    d = float(np.linalg.norm(direction))
    if d < 1e-6:
      return None
    direction = (direction / d).astype(np.float32)
    origin = origin.astype(np.float32)

    # Step size keyed off camera height so we don't undersample at low zoom.
    step = max(0.5, float(self.height) / 200.0)
    p = origin.copy()
    prev_above = p[1] > self._terrain_h_at(p[0], p[2])
    for _ in range(1500):
      p = p + direction * step
      if p[0] < -1.0 or p[2] < -1.0 or p[0] > self._map_w or p[2] > self._map_h:
        if not prev_above:
          break
        continue
      th = self._terrain_h_at(p[0], p[2])
      above = p[1] > th
      if prev_above and not above:
        # Refine by linear interp between previous and current sample.
        return np.array([p[0], th, p[2]], dtype=np.float32)
      prev_above = above
    return None

  # ── called every frame ────────────────────────────────────────────────────

  def update(self, dt: float) -> None:
    """Advance smooth-zoom spring and clamp camera above terrain."""
    self.target[1] = self._terrain_h_at(self.target[0], self.target[2])
    self.target[0] = float(np.clip(self.target[0], 0.0, float(self._map_w)))
    self.target[2] = float(np.clip(self.target[2], 0.0, float(self._map_h)))

    terrain_h      = self.target[1]
    min_h          = terrain_h + self.MIN_CLEARANCE
    self._h_target = max(min_h, self._h_target)

    alpha = min(1.0, self.ZOOM_SPRING * dt)
    self.height += (self._h_target - self.height) * alpha
    self.height  = max(min_h, self.height)

  # ── matrices ──────────────────────────────────────────────────────────────

  def position(self) -> NDArray:
    t     = math.radians(self.theta)
    p     = math.radians(self.pitch)
    horiz = self.height / math.tan(p)
    x = self.target[0] + horiz * math.sin(t)
    y = self.target[1] + self.height
    z = self.target[2] + horiz * math.cos(t)
    return np.array([x, y, z], dtype=np.float32)

  def view_matrix(self) -> NDArray:
    return self.look_at(
      self.position(),
      self.target,
      np.array([0.0, 1.0, 0.0], dtype=np.float32),
    )

  def projection_matrix(self, aspect: float, width: int = 0, height: int = 0) -> NDArray:
    return self.perspective(self.fov, aspect, self.near, self.far)

  # ── input handlers ────────────────────────────────────────────────────────

  def orbit(self, dx: float, dy: float) -> None:
    """Orbit camera in a half-dome around the screen-centre terrain pivot.
    dx = yaw delta, dy = pitch delta (both in screen pixels).
    Pitch clamped to [15°, 75°]. Camera is lifted over terrain if yaw
    swings it behind a hill."""
    self.theta += dx * self.ORBIT_SENS

    # After yaw change, raise h_target if the new camera position clips terrain.
    p     = math.radians(self.pitch)
    tan_p = math.tan(p)
    if tan_p > 1e-6:
      t     = math.radians(self.theta)
      horiz = self.height / tan_p
      cx    = self.target[0] + horiz * math.sin(t)
      cz    = self.target[2] + horiz * math.cos(t)
      min_h = self._terrain_h_at(cx, cz) + self.MIN_CLEARANCE - float(self.target[1])
      if min_h > self._h_target:
        self._h_target = min_h

    if dy == 0.0:
      return
    new_pitch = max(15.0, min(75.0, self.pitch + dy * self.ORBIT_SENS))
    p     = math.radians(new_pitch)
    tan_p = math.tan(p)
    if tan_p > 1e-6:
      t     = math.radians(self.theta)
      horiz = self.height / tan_p
      cx    = self.target[0] + horiz * math.sin(t)
      cz    = self.target[2] + horiz * math.cos(t)
      cam_y = float(self.target[1]) + self.height
      if cam_y < self._terrain_h_at(cx, cz) + self.MIN_CLEARANCE:
        return   # pitch would clip terrain — keep current
    self.pitch = new_pitch

  def zoom(self, direction: int) -> None:
    """Zoom in/out with smart pivot: zooming in shifts the pivot toward the
    terrain point under the screen centre for a natural 'zoom toward cursor' feel."""
    if direction > 0:
      hit = self._raycast_center()
      if hit is not None:
        self.target += (hit - self.target) * 0.15
    step = self._h_target * self.ZOOM_STEP
    self._h_target -= direction * step
    self._h_target = min(3_000.0, self._h_target)  # min enforced in update()

  def pan_keys(self, dx: float, dz: float, dt: float) -> None:
    """WASD / arrow-key pan. dx/dz are unit direction values (−1, 0, +1)."""
    speed = self.EDGE_SPEED * (self.height / 300.0) * dt
    self._apply_pan(dx * speed, dz * speed)

  def pan_mouse(self, screen_dx: float, screen_dy: float) -> None:
    """Middle-mouse grab-drag pan."""
    scale = self.height * self.MAP_PAN_SENS
    self._apply_pan(screen_dx * scale, screen_dy * scale)

  def _apply_pan(self, dx: float, dz: float) -> None:
    """Apply a camera-local pan to the world-space target pivot.

    Sign convention (matches edge-scroll and WASD):
      dx > 0  →  camera-right  (world: +cos θ, −sin θ in XZ)
      dz < 0  →  camera-forward (world: −sin θ, −cos θ in XZ)

    The correct world transform is the TRANSPOSE (= inverse) rotation:
      world_x  =  dx·cos θ  +  dz·sin θ
      world_z  = −dx·sin θ  +  dz·cos θ
    """
    t  = math.radians(self.theta)
    ct = math.cos(t)
    st = math.sin(t)
    self.target[0] +=  dx * ct + dz * st
    self.target[2] += -dx * st + dz * ct

  # ── utility ───────────────────────────────────────────────────────────────

  def fit_map(self, map_size: int = 512) -> None:
    half           = map_size * 0.5
    self.target    = np.array([half, 0.0, half], dtype=np.float32)
    self.pitch     = 55.0
    self.theta     = 0.0
    self.height    = map_size * 0.8
    self._h_target = self.height
    self.near      = 1.0
    self.far       = float(map_size) * 30.0

  def reset(self) -> None:
    self.fit_map()
