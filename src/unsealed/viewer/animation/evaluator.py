"""
Skeletal animation evaluator.

Given a ViewerSkeleton and a ViewerAnimationGroup, computes per-bone
skinning matrices at any given time by interpolating keyframes.

Key convention:
  .an1 keyframes store LOCAL-SPACE bone transforms (relative to the parent
  bone), matching GLTF's node TRS convention.  The GLTF encoder confirms
  this: bind-pose nodes are converted from world to local, but animation
  keyframe values are exported raw — meaning the raw values are already
  local-space and need parent composition to reach world space.

  For bones that have no track in the current animation group the bind-pose
  local matrix is used so that vertices stay at their rest position even when
  a parent bone is animated.

No file I/O, no OpenGL — pure numpy maths.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
from numpy.typing import NDArray

from ..scenes import (
  ViewerAnimationGroup,
  ViewerBoneAnimation,
  ViewerSkeleton,
)
from .sampling import _matrix_to_quat, _sample_quat, _sample_vec3, _trs_matrix


class NodeAnimator:
  """
  Evaluates a single node's transform animation at a specific time.

  Used for non-physique (non-skinned) ms1 map objects where the .an1 file
  targets the mesh node by name directly — mirroring what Three.js
  AnimationMixer does when it targets a scene node's translation/rotation/scale.

  The bind-pose matrix (model_matrix) supplies default T/R/S values for
  any tracks that are absent in the animation group.
  """

  def __init__(self, ba: ViewerBoneAnimation, bind_model_matrix: NDArray) -> None:
    self._ba = ba
    # Decompose bind-pose model matrix → defaults for absent tracks
    rot_scale = bind_model_matrix[:3, :3]
    sca = np.linalg.norm(rot_scale, axis=0)
    sca_safe = np.where(sca > 1e-9, sca, np.float32(1.0))
    rot_mat = rot_scale / sca_safe
    self._default_T = bind_model_matrix[:3, 3].copy().astype(np.float32)
    self._default_R = _matrix_to_quat(rot_mat)
    self._default_S = sca.astype(np.float32)

  def compute(self, time: float) -> NDArray:
    """Return animated 4×4 float32 model matrix at *time* (seconds)."""
    T = _sample_vec3(self._ba.translations, time, self._default_T)
    R = _sample_quat(self._ba.rotations, time, self._default_R)
    S = _sample_vec3(self._ba.scales, time, self._default_S)
    return _trs_matrix(T, R, S)


class Animator:
  """
  Evaluates a skeletal animation at a specific time.

  Usage::

      animator = Animator(skeleton, animation_group)
      bone_matrices = animator.compute(time_sec)   # List[NDArray shape (4,4)]
      renderer.render(..., bone_matrices=bone_matrices)
  """

  def __init__(self, skeleton: ViewerSkeleton, group: ViewerAnimationGroup) -> None:
    self._skeleton = skeleton
    self._group = group

    # O(1) lookup: bone_name (and lowercased) → ViewerBoneAnimation
    self._anim_by_bone: dict = {}
    for ba in group.bone_animations:
      self._anim_by_bone[ba.bone_name] = ba
      self._anim_by_bone[ba.bone_name.lower()] = ba

    # Pre-compute bind-world matrices: inv(inverse_bind) = world_bind
    self._bind_world: List[NDArray] = [
      np.linalg.inv(b.inverse_bind).astype(np.float32) for b in skeleton.bones
    ]

    # Pre-compute LOCAL bind matrices for each bone.
    # local_bind[i] = inv(parent_world_bind) @ child_world_bind
    #               = parent_inverse_bind    @ child_world_bind
    # Root bones: local_bind = world_bind (no parent).
    self._local_bind: List[NDArray] = []
    for i, bone in enumerate(skeleton.bones):
      if bone.parent is None:
        local = self._bind_world[i].copy()
      else:
        pidx = skeleton.name_to_idx.get(bone.parent) or skeleton.name_to_idx.get(
          bone.parent.lower()
        )
        if pidx is not None:
          # inv(parent_world_bind) = parent.inverse_bind
          local = (skeleton.bones[pidx].inverse_bind @ self._bind_world[i]).astype(
            np.float32
          )
        else:
          local = self._bind_world[i].copy()
      self._local_bind.append(local)

    # Decompose local_bind to get per-bone default T / R / S.
    self._local_T: List[NDArray] = []
    self._local_R: List[NDArray] = []
    self._local_S: List[NDArray] = []
    for lb in self._local_bind:
      rot_scale = lb[:3, :3]
      sca = np.linalg.norm(rot_scale, axis=0)
      sca_safe = np.where(sca > 1e-9, sca, np.float32(1.0))
      rot_mat = rot_scale / sca_safe
      self._local_T.append(lb[:3, 3].copy().astype(np.float32))
      self._local_R.append(_matrix_to_quat(rot_mat))
      self._local_S.append(sca.astype(np.float32))

  def compute(self, time: float) -> List[NDArray]:
    """
    Return one (4,4) float32 skinning matrix per bone (same order as skeleton).

    Each matrix = world_animated @ inverse_bind.

    .an1 keyframes are local-space transforms, so each bone's world matrix
    is built by composing with the animated parent world matrix.
    Bones are assumed to be stored in topological order (parents first).
    """
    world_mats: List[Optional[NDArray]] = [None] * len(self._skeleton.bones)
    result: List[NDArray] = []

    for i, bone in enumerate(self._skeleton.bones):
      ba = self._anim_by_bone.get(bone.name) or self._anim_by_bone.get(
        bone.name.lower()
      )

      if ba is not None:
        T = _sample_vec3(ba.translations, time, self._local_T[i])
        R = _sample_quat(ba.rotations, time, self._local_R[i])
        S = _sample_vec3(ba.scales, time, self._local_S[i])
        local_mat = _trs_matrix(T, R, S)
      else:
        # No track for this bone → hold bind pose in local space
        local_mat = self._local_bind[i]

      # Compose with animated parent to get world matrix
      if bone.parent is None:
        world_mats[i] = local_mat
      else:
        pidx = self._skeleton.name_to_idx.get(
          bone.parent
        ) or self._skeleton.name_to_idx.get(bone.parent.lower())
        if pidx is not None and world_mats[pidx] is not None:
          world_mats[i] = world_mats[pidx] @ local_mat
        else:
          # Parent not yet computed (out-of-order) or unknown — use local as world
          world_mats[i] = local_mat

      sk_mat = (world_mats[i] @ bone.inverse_bind).astype(np.float32)
      result.append(sk_mat)

    return result
