"""AnimationSystem — stateless processor for AnimationComponent."""

from __future__ import annotations

from typing import Iterable, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from ...animation import Animator, NodeAnimator
from ...scene import MapScene, ModelScene
from ..components.animation import AnimationComponent


class AnimationSystem:
  def load(self, component: AnimationComponent, scene: ModelScene | MapScene) -> None:
    """Reset all animation state and initialise animators for the new scene."""
    self._reset(component)

    # Build name → mesh_idx lookup (scoped by source_file for map objects)
    component.mesh_src_name_to_idx = {
      (m.name.lower(), m.source_file): i for i, m in enumerate(scene.meshes)
    }

    if isinstance(scene, MapScene):
      self._init_map_animators(component, scene)
    elif isinstance(scene, ModelScene) and scene.animation_groups:
      component.enabled = True
      self.select(component, scene, 0)

  def _reset(self, component: AnimationComponent) -> None:
    """Clear all fields back to defaults."""
    component.enabled = False
    component.group_idx = 0
    component.time = 0.0
    component.playing = False
    component.animator = None
    component.bone_matrices = None
    component.node_animators = {}
    component.node_matrices = {}
    component.map_anim_states = {}
    component.mesh_skel_id = {}
    component.map_bone_matrices = {}
    component.map_node_anim_states = {}
    component.map_node_matrices = {}
    component.mesh_src_name_to_idx = {}

  def _init_map_animators(
    self, component: AnimationComponent, scene: MapScene
  ) -> None:
    """Set up per-object animators for map mode (mirrors viewer.js one-mixer-per-clone)."""
    for mesh_idx, mesh in enumerate(scene.meshes):
      if not mesh.animation_groups:
        continue
      group = mesh.animation_groups[0]

      if mesh.is_skinned and mesh.skeleton:
        skel_id = id(mesh.skeleton)
        component.mesh_skel_id[mesh_idx] = skel_id
        if skel_id not in component.map_anim_states:
          anim = Animator(mesh.skeleton, group)
          component.map_anim_states[skel_id] = [anim, 0.0, group.duration]

      elif not mesh.is_skinned:
        mesh_name_lc = mesh.name.lower()
        ba_match = next(
          (ba for ba in group.bone_animations if ba.bone_name.lower() == mesh_name_lc),
          None,
        )
        if ba_match is not None:
          local_mat = (
            mesh.local_model_matrix
            if mesh.local_model_matrix is not None
            else mesh.model_matrix
          )
          na = NodeAnimator(ba_match, local_mat)
          component.map_node_anim_states[mesh_idx] = [na, 0.0, group.duration]

    if component.map_anim_states or component.map_node_anim_states:
      print(
        f"[viewer] map animation: "
        f"{len(component.map_anim_states)} bone-anim type(s), "
        f"{len(component.map_node_anim_states)} node-anim mesh(es)"
      )

  def select(
    self, component: AnimationComponent, scene: ModelScene, idx: int
  ) -> None:
    """Switch to a different animation group and rebuild standalone animators."""
    if not scene.animation_groups:
      return
    component.group_idx = idx
    component.time = 0.0
    group = scene.animation_groups[idx]

    # Use bone animation only when the scene actually has skinned meshes.
    # A file can have a skeleton (e.g. a single dummy bone) without any
    # physique data — in that case node-transform animation must be used.
    has_skinned = any(m.is_skinned for m in scene.meshes)
    if scene.skeleton is not None and has_skinned:
      component.animator = Animator(scene.skeleton, group)
      component.bone_matrices = component.animator.compute(0.0)
    else:
      component.animator = None
      component.bone_matrices = None

    # Always build node animators for non-skinned meshes regardless of whether
    # a skeleton is present (bone and node animation are orthogonal).
    component.node_animators = {}
    component.node_matrices = {}
    for mesh_idx, mesh in enumerate(scene.meshes):
      if mesh.is_skinned:
        continue
      mesh_name_lc = mesh.name.lower()
      ba_match = next(
        (ba for ba in group.bone_animations if ba.bone_name.lower() == mesh_name_lc),
        None,
      )
      if ba_match is not None:
        local_mat = (
          mesh.local_model_matrix
          if mesh.local_model_matrix is not None
          else mesh.model_matrix
        )
        component.node_animators[mesh_idx] = NodeAnimator(ba_match, local_mat)
        component.node_matrices[mesh_idx] = component.node_animators[mesh_idx].compute(0.0)

  def toggle_play(self, component: AnimationComponent) -> None:
    if component.enabled:
      component.playing = not component.playing

  def stop(self, component: AnimationComponent) -> None:
    if component.enabled:
      component.playing = False
      component.time = 0.0
      if component.animator is not None:
        component.bone_matrices = component.animator.compute(0.0)

  def scrub(
    self, component: AnimationComponent, scene: ModelScene, delta: float
  ) -> None:
    """Move the playback cursor by delta seconds (only when paused)."""
    if not component.enabled or component.playing:
      return
    group = scene.animation_groups[component.group_idx]
    component.time = max(0.0, min(group.duration, component.time + delta))
    if component.animator is not None:
      component.bone_matrices = component.animator.compute(component.time)

  def update(
    self,
    component: AnimationComponent,
    scene: Optional[ModelScene | MapScene],
    dt: float,
  ) -> None:
    """Advance all active animators by dt seconds."""
    if scene is None:
      return

    if isinstance(scene, MapScene):
      self._update_map(component, scene, dt)

    self._update_standalone(component, scene, dt)

  def _compose_node_mats(
    self,
    component: AnimationComponent,
    scene: ModelScene | MapScene,
    animated_pairs: Iterable[Tuple[int, NDArray]],
  ) -> dict:
    """
    Compose local animated matrices with parent world matrices.

    Accepts an iterable of (mesh_idx, local_animated_matrix) pairs and returns
    a dict of world matrices, honouring parent_name hierarchy within the scene.
    """
    result: dict = {}
    for mesh_idx, local_animated in animated_pairs:
      mesh = scene.meshes[mesh_idx]
      if mesh.parent_name:
        p_idx = component.mesh_src_name_to_idx.get(
          (mesh.parent_name.lower(), mesh.source_file)
        )
        if p_idx is not None:
          parent_world = result.get(p_idx, scene.meshes[p_idx].model_matrix)
          result[mesh_idx] = np.asarray(parent_world @ local_animated, dtype=np.float32)
        else:
          result[mesh_idx] = local_animated
      else:
        result[mesh_idx] = local_animated
    return result

  def _update_map(
    self, component: AnimationComponent, scene: MapScene, dt: float
  ) -> None:
    """Advance map object animators (bone-based + node-transform)."""
    # Type A: bone-based (physique ms1 with skeleton)
    for state in component.map_anim_states.values():
      anim, t, dur = state
      if dur > 0.0:
        state[1] = (t + dt) % dur

    component.map_bone_matrices = {
      mesh_idx: component.map_anim_states[skel_id][0].compute(
        component.map_anim_states[skel_id][1]
      )
      for mesh_idx, skel_id in component.mesh_skel_id.items()
    }

    # Type B: node-transform (non-physique ms1, .an1 targets mesh node)
    for state in component.map_node_anim_states.values():
      na, t, dur = state
      if dur > 0.0:
        state[1] = (t + dt) % dur

    component.map_node_matrices = self._compose_node_mats(
      component,
      scene,
      ((idx, state[0].compute(state[1])) for idx, state in component.map_node_anim_states.items()),
    )

  def _update_standalone(
    self,
    component: AnimationComponent,
    scene: ModelScene | MapScene,
    dt: float,
  ) -> None:
    """Advance the standalone scene animation cursor and compute matrices."""
    if not component.enabled or not isinstance(scene, ModelScene):
      return

    group = scene.animation_groups[component.group_idx]

    if component.playing and group.duration > 0.0:
      component.time += dt
      component.time %= group.duration

    if component.animator is not None:
      component.bone_matrices = component.animator.compute(component.time)
    if component.node_animators:
      # Non-physique standalone ms1: compose parent_world @ local_animated
      component.node_matrices = self._compose_node_mats(
        component,
        scene,
        ((idx, na.compute(component.time)) for idx, na in component.node_animators.items()),
      )
