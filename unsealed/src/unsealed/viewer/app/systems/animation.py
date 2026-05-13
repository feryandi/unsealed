"""AnimationSystem — stateless processor for AnimationComponent.

Iterates `scene.entities` uniformly: each entity has its own playback state
in `component.states[i]`. After update(), `component.bone_matrices` and
`component.node_matrices` are flat dicts keyed by global mesh index, which
the renderer consumes through RenderContext.
"""

from __future__ import annotations

import numpy as np

from ...animation import Animator, NodeAnimator
from ...modes import AnimationPolicy, for_scene
from ...scenes import AnimatedEntity, ThreeDimensionalScene
from ..components.animation import AnimationComponent, EntityAnimState


class AnimationSystem:
  # ── lifecycle ─────────────────────────────────────────────────────────────

  def load(self, component: AnimationComponent, scene: object) -> None:
    """Build EntityAnimState per entity and prime mesh lookups."""
    self._reset(component)

    if not isinstance(scene, ThreeDimensionalScene):
      return

    mesh_to_idx = {id(m): i for i, m in enumerate(scene.meshes)}

    for ent_idx, entity in enumerate(scene.entities):
      state = EntityAnimState()

      for local_idx, mesh in enumerate(entity.meshes):
        gm_idx = mesh_to_idx.get(id(mesh))
        if gm_idx is None:
          continue
        component.mesh_to_entity[gm_idx] = ent_idx
        component.mesh_to_local[gm_idx] = local_idx
        component.mesh_src_name_to_idx[(mesh.name.lower(), entity.source_file)] = gm_idx

      if entity.animation_groups:
        state.enabled = True
        self._select_entity(state, entity, 0)

      component.states.append(state)

    # Apply the mode's policy for how to treat fresh entities.
    try:
      policy = for_scene(scene).animation_policy
    except ValueError:
      policy = AnimationPolicy()

    if policy.has_primary:
      for i, s in enumerate(component.states):
        if s.enabled:
          component.primary_entity = i
          break
    if policy.auto_play_all:
      for s in component.states:
        if s.enabled:
          s.playing = True

  # ── primary-entity controls (UI) ─────────────────────────────────────────

  def select(self, component: AnimationComponent, scene: object, idx: int) -> None:
    """Switch the primary entity's active animation group."""
    state = component.primary
    if state is None or not isinstance(scene, ThreeDimensionalScene):
      return
    entity = scene.entities[component.primary_entity]  # type: ignore[index]
    self._select_entity(state, entity, idx)

  def toggle_play(self, component: AnimationComponent) -> None:
    state = component.primary
    if state is not None and state.enabled:
      state.playing = not state.playing

  def stop(self, component: AnimationComponent) -> None:
    state = component.primary
    if state is None or not state.enabled:
      return
    state.playing = False
    state.time = 0.0
    if state.animator is not None:
      state.bone_matrices = state.animator.compute(0.0)

  def scrub(self, component: AnimationComponent, scene: object, delta: float) -> None:
    """Move primary entity's playback cursor (only when paused)."""
    state = component.primary
    if state is None or not state.enabled or state.playing:
      return
    state.time = max(0.0, min(state.duration, state.time + delta))
    if state.animator is not None:
      state.bone_matrices = state.animator.compute(state.time)

  # ── per-frame update ─────────────────────────────────────────────────────

  def update(self, component: AnimationComponent, scene: object, dt: float) -> None:
    """Advance every entity's clock and rebuild renderer-facing matrices."""
    if not isinstance(scene, ThreeDimensionalScene):
      return

    # 1. Advance each entity's time + compute per-entity matrices.
    for state in component.states:
      if not state.enabled or state.duration <= 0.0:
        continue
      if state.playing:
        state.time = (state.time + dt) % state.duration
      if state.animator is not None:
        state.bone_matrices = state.animator.compute(state.time)
      for local_idx, na in state.node_animators.items():
        state.node_matrices[local_idx] = na.compute(state.time)

    # 2. Flatten to renderer-facing per-mesh dicts. Process in scene.meshes
    #    order so children see their parents' already-composed world matrix.
    component.bone_matrices = {}
    component.node_matrices = {}

    for gm_idx, mesh in enumerate(scene.meshes):
      ent_idx = component.mesh_to_entity.get(gm_idx)
      if ent_idx is None:
        continue
      state = component.states[ent_idx]
      entity = scene.entities[ent_idx]
      local_idx = component.mesh_to_local[gm_idx]

      if mesh.is_skinned:
        if state.bone_matrices is not None:
          component.bone_matrices[gm_idx] = state.bone_matrices
        continue

      if local_idx not in state.node_matrices:
        continue
      local_animated = state.node_matrices[local_idx]
      component.node_matrices[gm_idx] = self._compose_parent(
        component, scene, entity, mesh, local_animated
      )

  # ── private ──────────────────────────────────────────────────────────────

  def _reset(self, component: AnimationComponent) -> None:
    component.states.clear()
    component.primary_entity = None
    component.bone_matrices.clear()
    component.node_matrices.clear()
    component.mesh_to_entity.clear()
    component.mesh_to_local.clear()
    component.mesh_src_name_to_idx.clear()

  def _select_entity(
    self, state: EntityAnimState, entity: AnimatedEntity, idx: int
  ) -> None:
    """Bind the entity's animator(s) to animation_groups[idx]; reset clock."""
    if not entity.animation_groups:
      return
    state.group_idx = idx
    state.time = 0.0
    group = entity.animation_groups[idx]
    state.duration = group.duration

    has_skinned = any(m.is_skinned for m in entity.meshes)
    if entity.skeleton is not None and has_skinned:
      state.animator = Animator(entity.skeleton, group)
      state.bone_matrices = state.animator.compute(0.0)
    else:
      state.animator = None
      state.bone_matrices = None

    state.node_animators = {}
    state.node_matrices = {}
    for local_idx, mesh in enumerate(entity.meshes):
      if mesh.is_skinned:
        continue
      mesh_name_lc = mesh.name.lower()
      ba_match = next(
        (ba for ba in group.bone_animations if ba.bone_name.lower() == mesh_name_lc),
        None,
      )
      if ba_match is None:
        continue
      local_mat = (
        mesh.local_model_matrix
        if mesh.local_model_matrix is not None
        else mesh.model_matrix
      )
      state.node_animators[local_idx] = NodeAnimator(ba_match, local_mat)
      state.node_matrices[local_idx] = state.node_animators[local_idx].compute(0.0)

  def _compose_parent(
    self,
    component: AnimationComponent,
    scene: ThreeDimensionalScene,
    entity: AnimatedEntity,
    mesh,
    local_animated,
  ):
    """Multiply local_animated by the parent's world matrix (animated or bind)."""
    if not mesh.parent_name:
      return local_animated
    p_idx = component.mesh_src_name_to_idx.get(
      (mesh.parent_name.lower(), entity.source_file)
    )
    if p_idx is None:
      return local_animated
    parent_world = component.node_matrices.get(p_idx)
    if parent_world is None:
      parent_world = scene.meshes[p_idx].model_matrix
    return np.asarray(parent_world @ local_animated, dtype=np.float32)
