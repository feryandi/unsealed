import numpy as np
from scipy.spatial.transform import Rotation as R


def decompose_mtx(mtx):
  """
  Decompose a 4x4 transformation matrix into translation, rotation, and scale.

  Handles matrices with negative determinant (left-handed/reflection) by
  absorbing the reflection into the scale component.

  Args:
    mtx: 4x4 numpy array representing a transformation matrix

  Returns:
    tuple: (loc, rot, sca) where:
      - loc: [x, y, z] translation vector
      - rot: [x, y, z, w] quaternion (GLTF format from scipy)
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
          f"Warning: Could not fix reflection matrix. Det before: {det:.6f}, after: {det_fixed:.6f}")
      print("Using identity rotation as fallback")
      rot_mtx = np.eye(3)

  # Convert rotation matrix to quaternion
  # SciPy returns [x, y, z, w], which matches GLTF format
  try:
    rot = R.from_matrix(rot_mtx).as_quat()
  except ValueError as e:
    # Fallback: if conversion still fails, use identity quaternion
    print(f"Warning: Failed to convert rotation matrix to quaternion: {e}")
    print(f"Matrix determinant: {np.linalg.det(rot_mtx):.6f}")
    print(f"Matrix:\n{rot_mtx}")
    # Identity quaternion: no rotation
    rot = np.array([0.0, 0.0, 0.0, 1.0])

  return loc, rot, sca
