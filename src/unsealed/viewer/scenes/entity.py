"""AnimatedEntity — a self-contained animated unit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .scene import ViewerAnimationGroup, ViewerMesh, ViewerSkeleton


@dataclass
class AnimatedEntity:
  """
  One or more meshes that share a skeleton and animation timeline.

  A ModelScene has exactly one entity (the whole model). A MapScene has one
  entity per object type, covering every map instance of that file. The same
  AnimatedEntity shape works for both — `AnimationSystem` iterates entities
  uniformly with no scene-type branches.

  Membership: `meshes` are the *same* `ViewerMesh` instances that appear in
  the scene's flat `meshes` list (the renderer iterates that list). The entity
  doesn't own the meshes exclusively; it groups them for animation purposes.
  """

  name: str
  meshes: List[ViewerMesh] = field(default_factory=list)
  skeleton: Optional[ViewerSkeleton] = None
  animation_groups: List[ViewerAnimationGroup] = field(default_factory=list)
  # Original source file (e.g. "fence01.ms1") — set for map-object entities.
  source_file: Optional[str] = None
