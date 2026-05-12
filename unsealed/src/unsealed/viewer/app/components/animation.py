"""AnimationComponent — per-entity playback state + flat renderer-facing matrices."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from numpy.typing import NDArray

if TYPE_CHECKING:
  from ...animation import Animator, NodeAnimator


@dataclass
class EntityAnimState:
  """Playback state for a single AnimatedEntity.

  An entity is "enabled" when it has at least one animation_group. Bone-based
  matrices are computed when the entity has a skeleton AND any skinned mesh;
  node-based matrices are computed for non-skinned meshes whose name matches
  an animation track.
  """
  enabled: bool = False
  group_idx: int = 0
  time: float = 0.0
  playing: bool = False
  duration: float = 0.0

  # Bone-based (skinned meshes share these matrices via the entity's skeleton).
  animator: "Optional[Animator]" = None
  bone_matrices: "Optional[List[NDArray]]" = None

  # Node-based — keyed by ENTITY-LOCAL mesh index (position inside entity.meshes).
  node_animators: "Dict[int, NodeAnimator]" = field(default_factory=dict)
  node_matrices: "Dict[int, NDArray]" = field(default_factory=dict)


@dataclass
class AnimationComponent:
  """All animation state. One EntityAnimState per scene entity.

  After `AnimationSystem.update(...)`, the renderer reads `bone_matrices` and
  `node_matrices` — flat dicts keyed by GLOBAL mesh index (index into
  `scene.meshes`). Both dicts contain only entries for meshes that are
  actively animated this frame.

  `primary_entity` is the entity controllable by the UI (model mode = entity
  0; map mode = None — all entities auto-play).
  """
  states: List[EntityAnimState] = field(default_factory=list)
  primary_entity: Optional[int] = None

  # Renderer-facing flat dicts keyed by GLOBAL mesh index (scene.meshes idx).
  bone_matrices: Dict[int, List[NDArray]] = field(default_factory=dict)
  node_matrices: Dict[int, NDArray] = field(default_factory=dict)

  # Lookup helpers rebuilt at each `load()` call.
  mesh_to_entity: Dict[int, int] = field(default_factory=dict)   # global mesh idx → entity idx
  mesh_to_local: Dict[int, int] = field(default_factory=dict)    # global mesh idx → entity-local mesh idx
  # (mesh_name_lc, source_file) → global mesh idx — for parent-mesh hierarchy lookups.
  mesh_src_name_to_idx: Dict[Tuple[str, Optional[str]], int] = field(default_factory=dict)

  # ── UI convenience ───────────────────────────────────────────────────────

  @property
  def primary(self) -> Optional[EntityAnimState]:
    """The EntityAnimState the UI controls, or None in non-primary modes."""
    if self.primary_entity is None or self.primary_entity >= len(self.states):
      return None
    return self.states[self.primary_entity]
