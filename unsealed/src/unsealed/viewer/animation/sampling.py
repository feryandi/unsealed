"""
Keyframe sampling utilities for skeletal and node animation.

No file I/O, no OpenGL — pure numpy maths.
"""

from __future__ import annotations

import math
from typing import List

import numpy as np
from numpy.typing import NDArray

from ..scene import ViewerKeyframe


def _find_keyframe_pair(
  keyframes: List[ViewerKeyframe], time: float
) -> tuple[int, int]:
  """Binary-search for the bracketing keyframe indices (lo, hi) at *time*."""
  lo, hi = 0, len(keyframes) - 1
  while lo + 1 < hi:
    mid = (lo + hi) // 2
    if keyframes[mid].time <= time:
      lo = mid
    else:
      hi = mid
  return lo, hi


def _sample_vec3(
  keyframes: List[ViewerKeyframe], time: float, default: NDArray
) -> NDArray:
  """Linearly interpolate a vec3 track at *time* (seconds)."""
  if not keyframes:
    return default.copy()
  if len(keyframes) == 1 or time <= keyframes[0].time:
    return keyframes[0].value.copy()
  if time >= keyframes[-1].time:
    return keyframes[-1].value.copy()

  lo, hi = _find_keyframe_pair(keyframes, time)
  t0, t1 = keyframes[lo].time, keyframes[hi].time
  dt = t1 - t0
  if dt < 1e-9:
    return keyframes[lo].value.copy()
  alpha = (time - t0) / dt
  return (
    keyframes[lo].value + alpha * (keyframes[hi].value - keyframes[lo].value)
  ).astype(np.float32)


def _sample_quat(
  keyframes: List[ViewerKeyframe], time: float, default: NDArray | None = None
) -> NDArray:
  """SLERP a quaternion [x,y,z,w] track at *time* (seconds)."""
  if not keyframes:
    return (
      default.copy()
      if default is not None
      else np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
    )
  if len(keyframes) == 1 or time <= keyframes[0].time:
    return keyframes[0].value.copy()
  if time >= keyframes[-1].time:
    return keyframes[-1].value.copy()

  lo, hi = _find_keyframe_pair(keyframes, time)
  t0, t1 = keyframes[lo].time, keyframes[hi].time
  dt = t1 - t0
  if dt < 1e-9:
    return keyframes[lo].value.copy()
  alpha = float((time - t0) / dt)
  return _slerp(keyframes[lo].value, keyframes[hi].value, alpha)


def _slerp(q1: NDArray, q2: NDArray, t: float) -> NDArray:
  """Quaternion SLERP. Both quats as [x,y,z,w]."""
  n1 = float(np.linalg.norm(q1))
  n2 = float(np.linalg.norm(q2))
  q1 = q1 / n1 if n1 > 1e-9 else q1
  q2 = q2 / n2 if n2 > 1e-9 else q2

  dot = float(np.dot(q1, q2))
  if dot < 0.0:  # take the short arc
    q2 = -q2
    dot = -dot
  dot = min(dot, 1.0)

  if dot > 0.9995:  # nearly identical → stable linear fallback
    result = q1 + t * (q2 - q1)
    n = float(np.linalg.norm(result))
    return (result / n if n > 1e-9 else result).astype(np.float32)

  theta_0 = float(np.arccos(dot))
  theta = theta_0 * t
  sin_theta = float(np.sin(theta))
  sin_theta_0 = float(np.sin(theta_0))
  s1 = float(np.cos(theta)) - dot * sin_theta / sin_theta_0
  s2 = sin_theta / sin_theta_0
  return (s1 * q1 + s2 * q2).astype(np.float32)


def _trs_matrix(t: NDArray, r: NDArray, s: NDArray) -> NDArray:
  """
  Build a row-major 4×4 TRS matrix from:
    t : translation  (3,)
    r : rotation quaternion [x,y,z,w]  (4,)
    s : scale  (3,)

  Scale is applied to COLUMNS of the rotation matrix (matching decompose_mtx
  which measures scale as column norms) so that:
    np.array(bone.tm).T  ==  _trs_matrix(bone.loc, bone.rot, bone.sca)
  """
  n = float(np.linalg.norm(r))
  q = r / n if n > 1e-9 else np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
  x, y, z, w = float(q[0]), float(q[1]), float(q[2]), float(q[3])

  m = np.identity(4, dtype=np.float32)

  # Standard quaternion → rotation matrix
  m[0, 0] = 1.0 - 2.0 * (y * y + z * z)
  m[0, 1] = 2.0 * (x * y - z * w)
  m[0, 2] = 2.0 * (x * z + y * w)
  m[1, 0] = 2.0 * (x * y + z * w)
  m[1, 1] = 1.0 - 2.0 * (x * x + z * z)
  m[1, 2] = 2.0 * (y * z - x * w)
  m[2, 0] = 2.0 * (x * z - y * w)
  m[2, 1] = 2.0 * (y * z + x * w)
  m[2, 2] = 1.0 - 2.0 * (x * x + y * y)

  # Scale is applied to columns (decompose_mtx uses column norms as scale)
  m[:3, 0] *= s[0]
  m[:3, 1] *= s[1]
  m[:3, 2] *= s[2]

  # translation last column (row-major matrix)
  m[0, 3] = t[0]
  m[1, 3] = t[1]
  m[2, 3] = t[2]
  return m


def _matrix_to_quat(m: NDArray) -> NDArray:
  """
  Convert a 3×3 rotation matrix to a quaternion [x,y,z,w].
  Uses Shepperd's method for numerical stability.
  """
  trace = float(m[0, 0] + m[1, 1] + m[2, 2])
  if trace > 0.0:
    s = 0.5 / math.sqrt(trace + 1.0)
    w = 0.25 / s
    x = (float(m[2, 1]) - float(m[1, 2])) * s
    y = (float(m[0, 2]) - float(m[2, 0])) * s
    z = (float(m[1, 0]) - float(m[0, 1])) * s
  elif float(m[0, 0]) > float(m[1, 1]) and float(m[0, 0]) > float(m[2, 2]):
    s = 2.0 * math.sqrt(1.0 + float(m[0, 0]) - float(m[1, 1]) - float(m[2, 2]))
    w = (float(m[2, 1]) - float(m[1, 2])) / s
    x = 0.25 * s
    y = (float(m[0, 1]) + float(m[1, 0])) / s
    z = (float(m[0, 2]) + float(m[2, 0])) / s
  elif float(m[1, 1]) > float(m[2, 2]):
    s = 2.0 * math.sqrt(1.0 + float(m[1, 1]) - float(m[0, 0]) - float(m[2, 2]))
    w = (float(m[0, 2]) - float(m[2, 0])) / s
    x = (float(m[0, 1]) + float(m[1, 0])) / s
    y = 0.25 * s
    z = (float(m[1, 2]) + float(m[2, 1])) / s
  else:
    s = 2.0 * math.sqrt(1.0 + float(m[2, 2]) - float(m[0, 0]) - float(m[1, 1]))
    w = (float(m[1, 0]) - float(m[0, 1])) / s
    x = (float(m[0, 2]) + float(m[2, 0])) / s
    y = (float(m[1, 2]) + float(m[2, 1])) / s
    z = 0.25 * s
  return np.array([x, y, z, w], dtype=np.float32)
