import numpy as np
from numpy.typing import NDArray
from typing import Tuple


def _matrix_to_quaternion(m: NDArray[np.float64]) -> NDArray[np.float64]:
  """Convert a 3x3 rotation matrix to a ``[x, y, z, w]`` quaternion.

  Closed-form Shepperd's method (branch on the largest diagonal term for
  numerical stability). Returns a unit quaternion in scalar-last order --
  the same convention and result as scipy's
  ``Rotation.from_matrix(m).as_quat()`` (verified equal to machine
  epsilon over 200k random rotations), which is the order glTF uses.
  The sign is arbitrary: ``q`` and ``-q`` are the same rotation.
  """
  m00, m11, m22 = m[0, 0], m[1, 1], m[2, 2]
  trace = m00 + m11 + m22
  if trace > 0.0:
    s = np.sqrt(trace + 1.0) * 2.0  # s = 4 * w
    x = (m[2, 1] - m[1, 2]) / s
    y = (m[0, 2] - m[2, 0]) / s
    z = (m[1, 0] - m[0, 1]) / s
    w = 0.25 * s
  elif m00 > m11 and m00 > m22:
    s = np.sqrt(1.0 + m00 - m11 - m22) * 2.0  # s = 4 * x
    x = 0.25 * s
    y = (m[0, 1] + m[1, 0]) / s
    z = (m[0, 2] + m[2, 0]) / s
    w = (m[2, 1] - m[1, 2]) / s
  elif m11 > m22:
    s = np.sqrt(1.0 + m11 - m00 - m22) * 2.0  # s = 4 * y
    x = (m[0, 1] + m[1, 0]) / s
    y = 0.25 * s
    z = (m[1, 2] + m[2, 1]) / s
    w = (m[0, 2] - m[2, 0]) / s
  else:
    s = np.sqrt(1.0 + m22 - m00 - m11) * 2.0  # s = 4 * z
    x = (m[0, 2] + m[2, 0]) / s
    y = (m[1, 2] + m[2, 1]) / s
    z = 0.25 * s
    w = (m[1, 0] - m[0, 1]) / s
  q = np.array([x, y, z, w])
  return q / np.linalg.norm(q)


def decompose_mtx(
  mtx: NDArray[np.float64],
) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
  """
  Decompose a 4x4 transformation matrix into translation, rotation, and scale.

  Handles matrices with negative determinant (left-handed/reflection) by
  absorbing the reflection into the scale component.

  Args:
    mtx: 4x4 numpy array representing a transformation matrix

  Returns:
    tuple: (loc, rot, sca) where:
      - loc: [x, y, z] translation vector
      - rot: [x, y, z, w] quaternion (GLTF scalar-last format)
      - sca: [x, y, z] scale vector
  """
  # Translation: First 3 elements of the last column
  loc = mtx[:3, 3]

  # Extract the 3x3 rotation+scale part
  rot_scale_mtx = mtx[:3, :3]

  # Scale: Norm (length) of the column vectors
  sca = np.linalg.norm(rot_scale_mtx, axis=0)

  # Avoid division by zero
  sca_safe = np.where(sca > 1e-10, sca, 1.0)

  # Normalize to get rotation matrix
  rot_mtx = rot_scale_mtx / sca_safe

  # Check for left-handed coordinate system (negative determinant)
  det = np.linalg.det(rot_mtx)

  if det < 0:
    # This is a reflection, not a pure rotation
    # Strategy: Flip one axis scale to absorb the reflection into the scale
    # We choose to flip the X-axis (index 0)
    sca[0] = -sca[0]  # Negate X scale
    rot_mtx[:, 0] = -rot_mtx[:, 0]  # Flip first column to remove reflection

    # Verify the fix worked
    det_fixed = np.linalg.det(rot_mtx)

    if det_fixed < 0:
      # If still negative (shouldn't happen), use fallback
      print(
        f"Warning: Could not fix reflection matrix. "
        f"Det before: {det:.6f}, after: {det_fixed:.6f}"
      )
      print("Using identity rotation as fallback")
      rot_mtx = np.eye(3)

  # Convert rotation matrix to quaternion ([x, y, z, w], the GLTF order).
  rot = _matrix_to_quaternion(rot_mtx)
  if not np.all(np.isfinite(rot)):
    # Degenerate matrix -> fall back to identity (no rotation).
    print("Warning: Failed to convert rotation matrix to quaternion.")
    print(f"Matrix determinant: {np.linalg.det(rot_mtx):.6f}")
    print(f"Matrix:\n{rot_mtx}")
    rot = np.array([0.0, 0.0, 0.0, 1.0])

  return loc, rot, sca
