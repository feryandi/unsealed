"""
ray_pick.py — CPU ray-AABB picking helpers.
"""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from .registry import RenderRegistry


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

  try:
    inv_vp = np.linalg.inv((proj @ view).astype(np.float64))
  except np.linalg.LinAlgError:
    return np.zeros(3, dtype=np.float32), np.array([0, 0, -1], dtype=np.float32)

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


def ray_aabb_intersect(
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

  return ray_aabb_intersect(local_origin, local_dir, aabb_min, aabb_max)


def pick(
  registry: RenderRegistry,
  mx: int,
  my: int,
  width: int,
  height: int,
  view: NDArray,
  proj: NDArray,
  mirror_x: NDArray,
) -> Optional[int]:
  """CPU ray-cast pick against mesh AABBs. Returns nearest entity_id or None."""
  if not registry.buffers:
    return None

  proj = mirror_x @ proj

  ray_origin, ray_dir = unproject_ray(mx, my, width, height, view, proj)

  best_t = float("inf")
  best_idx: Optional[int] = None

  for eid in registry.entity_ids():
    buf = registry.buffers[eid]
    xform = registry.transforms[eid]
    bnds = registry.bounds[eid]

    if buf.inst_mats_cpu is not None:
      for k in range(buf.instance_count):
        world = buf.inst_mats_cpu[k] @ xform.model_matrix
        t = ray_aabb_in_world(
          ray_origin, ray_dir, bnds.aabb_min, bnds.aabb_max, world
        )
        if t is not None and 0.0 < t < best_t:
          best_t = t
          best_idx = eid
    else:
      t = ray_aabb_in_world(
        ray_origin, ray_dir, bnds.aabb_min, bnds.aabb_max, xform.model_matrix
      )
      if t is not None and 0.0 < t < best_t:
        best_t = t
        best_idx = eid

  return best_idx
