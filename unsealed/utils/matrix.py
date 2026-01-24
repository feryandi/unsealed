import numpy as np
from scipy.spatial.transform import Rotation as R


def decompose_mtx(mtx):
  # Translation: First 3 elements of the last column
  loc = mtx[:3, 3]

  # Scale: Norm (length) of the column vectors of the 3x3 rotation part
  sca = np.linalg.norm(mtx[:3, :3], axis=0)

  # Rotation: Normalize the 3x3 part and convert to Quaternion
  # Note: SciPy returns [x, y, z, w], which matches GLTF
  rot_mtx = mtx[:3, :3] / sca
  rot = R.from_matrix(rot_mtx).as_quat()

  return loc, rot, sca
