from dataclasses import dataclass, field
from typing import List

from .entity import AnimatedEntity
from .scene import ViewerMesh
from .viewer_scene import ViewerScene


@dataclass
class ThreeDimensionalScene(ViewerScene):
  """Base for 3-D viewer scenes (ModelScene, MapScene).

  `meshes` is the flat list the renderer iterates. `entities` groups meshes
  that share a skeleton + animation timeline (one per model file). Each mesh
  in `meshes` belongs to exactly one entity in `entities`.
  """

  meshes: List[ViewerMesh] = field(default_factory=list)
  entities: List[AnimatedEntity] = field(default_factory=list)
