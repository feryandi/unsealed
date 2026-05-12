from dataclasses import dataclass, field
from typing import List

from numpy.typing import NDArray
import numpy as np

from .three_dimensional_scene import ThreeDimensionalScene


@dataclass
class ModelScene(ThreeDimensionalScene):
  """Scene for a single 3-D mesh or actor (ms1 / act)."""

  bounds_center: NDArray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))
  bounds_radius: float = 1.0
  tri_count: int = 0

  @property
  def mesh_names(self) -> List[str]:
    return [m.name for m in self.meshes]
