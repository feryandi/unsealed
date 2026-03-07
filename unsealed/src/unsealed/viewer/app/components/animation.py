"""AnimationComponent — pure data, no logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from numpy.typing import NDArray

if TYPE_CHECKING:
  from ...animation import Animator, NodeAnimator


@dataclass
class AnimationComponent:
  # Standalone scene animation
  enabled: bool = False
  group_idx: int = 0
  time: float = 0.0
  playing: bool = False
  animator: "Optional[Animator]" = None
  bone_matrices: "Optional[List[NDArray]]" = None
  node_animators: "Dict[int, NodeAnimator]" = field(default_factory=dict)
  node_matrices: "Dict[int, NDArray]" = field(default_factory=dict)

  # Map bone-based animation
  map_anim_states: "Dict[int, List[Any]]" = field(default_factory=dict)   # skel_id → [Animator, t, dur]
  mesh_skel_id: "Dict[int, int]" = field(default_factory=dict)            # mesh_idx → skel_id
  map_bone_matrices: "Dict[int, List[NDArray]]" = field(default_factory=dict)

  # Map node-transform animation
  map_node_anim_states: "Dict[int, List[Any]]" = field(default_factory=dict)  # mesh_idx → [NodeAnimator, t, dur]
  map_node_matrices: "Dict[int, NDArray]" = field(default_factory=dict)

  # Name lookup for parent hierarchy
  mesh_src_name_to_idx: "Dict[Tuple[str, Optional[str]], int]" = field(default_factory=dict)
