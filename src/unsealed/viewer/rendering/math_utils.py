"""Renderer math helpers — billboard, Q3 texMatrix, picking.

Pure-numpy utilities used by the forward/Q3/picking paths. Kept out of
`renderer.py` so the orchestrator stays focused on per-frame flow.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray


# ─── Billboard helper ────────────────────────────────────────────────────────


def spherical_billboard(model_mat: NDArray, view: NDArray) -> NDArray:
  """Replace model_mat's rotation with the camera's orientation so the
  geometry always faces the camera (spherical billboard).

  Position and per-axis scale are preserved from model_mat. View matrix
  rows are interpreted as [right, up, -forward] in world space.
  """
  pos = model_mat[:3, 3]
  scale_x = float(np.linalg.norm(model_mat[:3, 0]))
  scale_y = float(np.linalg.norm(model_mat[:3, 1]))
  scale_z = float(np.linalg.norm(model_mat[:3, 2]))

  right = view[0, :3]
  up = view[1, :3]
  fwd = -view[2, :3]

  bb = np.identity(4, dtype=np.float32)
  bb[:3, 0] = right * scale_x
  bb[:3, 1] = up * scale_y
  bb[:3, 2] = fwd * scale_z
  bb[:3, 3] = pos
  return bb


# ─── Q3 texture matrix helper ────────────────────────────────────────────────


def compute_tex_matrix(
  tc_mods: List[Tuple[str, Tuple[float, ...]]], time: float
) -> NDArray:
  """Compose a column-major 3×3 UV-transform matrix from a list of tcMod ops.

  Supported ops:
    ("rotate",  (deg_per_sec,))
    ("scroll",  (s_per_sec, t_per_sec))
    ("scale",   (s, t))

  Returns a flat float32 array of 9 values in column-major order
  (suitable for glUniformMatrix3fv with GL_FALSE transpose flag).
  """
  result = np.identity(3, dtype=np.float64)

  for mod_type, params in tc_mods:
    if mod_type == "rotate" and len(params) >= 1:
      angle = np.radians(params[0] * time)
      cos_a, sin_a = np.cos(angle), np.sin(angle)
      # Rotate around UV centre (0.5, 0.5): T(-0.5) R T(0.5)
      t_to = np.array([[1, 0, -0.5], [0, 1, -0.5], [0, 0, 1]], dtype=np.float64)
      rot = np.array(
        [[cos_a, -sin_a, 0], [sin_a, cos_a, 0], [0, 0, 1]], dtype=np.float64
      )
      t_back = np.array([[1, 0, 0.5], [0, 1, 0.5], [0, 0, 1]], dtype=np.float64)
      result = t_back @ rot @ t_to @ result

    elif mod_type == "scroll" and len(params) >= 2:
      # Q3 scroll is in game UV space (V=0 at top). Vertex shader flips V
      # into GL UV space before applying this matrix, so T must be negated
      # to preserve direction.
      tx, ty = params[0] * time, -params[1] * time
      trans = np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]], dtype=np.float64)
      result = trans @ result

    elif mod_type == "scale" and len(params) >= 2:
      sx, sy = params[0], params[1]
      scale = np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], dtype=np.float64)
      result = scale @ result

  return result.T.astype(np.float32).flatten()


# ─── Ray picking helpers ──────────────────────────────────────────────────────


def unproject_ray(
  mx: int,
  my: int,
  width: int,
  height: int,
  view: NDArray,
  proj: NDArray,
) -> Tuple[NDArray, NDArray]:
  """Return (ray_origin, ray_dir) in world space from a screen pixel."""
  ndc_x = (2.0 * mx / width) - 1.0
  ndc_y = 1.0 - (2.0 * my / height)

  inv_vp = np.linalg.inv((proj @ view).astype(np.float64))

  near = inv_vp @ np.array([ndc_x, ndc_y, -1.0, 1.0], dtype=np.float64)
  far = inv_vp @ np.array([ndc_x, ndc_y, 1.0, 1.0], dtype=np.float64)
  near /= near[3]
  far /= far[3]

  origin = near[:3].astype(np.float32)
  direc = (far[:3] - near[:3]).astype(np.float32)
  length = np.linalg.norm(direc)
  if length > 1e-8:
    direc /= length
  return origin, direc


def _ray_aabb_intersect(
  origin: NDArray,
  direction: NDArray,
  aabb_min: NDArray,
  aabb_max: NDArray,
) -> Optional[float]:
  """Slab-method ray–AABB test. Returns world-space t or None on miss."""
  t_min = -np.inf
  t_max = np.inf
  for i in range(3):
    if abs(direction[i]) < 1e-8:
      if origin[i] < aabb_min[i] or origin[i] > aabb_max[i]:
        return None
    else:
      t1 = (aabb_min[i] - origin[i]) / direction[i]
      t2 = (aabb_max[i] - origin[i]) / direction[i]
      if t1 > t2:
        t1, t2 = t2, t1
      t_min = max(t_min, t1)
      t_max = min(t_max, t2)
  if t_max < 0.0 or t_min > t_max:
    return None
  return t_min if t_min >= 0.0 else t_max


def ray_aabb_in_world(
  ray_origin: NDArray,
  ray_dir: NDArray,
  aabb_min: NDArray,
  aabb_max: NDArray,
  world_matrix: NDArray,
) -> Optional[float]:
  """Transform a world-space ray into local space and test against the local AABB."""
  try:
    inv_world = np.linalg.inv(world_matrix.astype(np.float64))
  except np.linalg.LinAlgError:
    return None

  o4 = np.array([*ray_origin, 1.0], dtype=np.float64)
  d4 = np.array([*ray_dir, 0.0], dtype=np.float64)

  local_origin = (inv_world @ o4)[:3].astype(np.float32)
  local_dir = (inv_world @ d4)[:3].astype(np.float32)

  return _ray_aabb_intersect(local_origin, local_dir, aabb_min, aabb_max)
