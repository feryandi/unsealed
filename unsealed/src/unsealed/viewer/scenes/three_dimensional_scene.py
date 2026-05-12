from dataclasses import dataclass, field
from typing import List, Optional

from .scene import ViewerAnimationGroup, ViewerMesh, ViewerSkeleton
from .viewer_scene import ViewerScene


@dataclass
class ThreeDimensionalScene(ViewerScene):
  """3D viewer scenes. For example: ModelScene, or MapScene."""

  meshes: List[ViewerMesh] = field(default_factory=list)
  skeleton: Optional[ViewerSkeleton] = None
  animation_groups: List[ViewerAnimationGroup] = field(default_factory=list)
