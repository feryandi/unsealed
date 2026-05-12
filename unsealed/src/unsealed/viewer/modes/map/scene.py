"""MapScene — scene type for .map files."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from numpy.typing import NDArray

from ...scenes import ViewerMesh
from ...scenes.three_dimensional_scene import ThreeDimensionalScene


@dataclass
class MapScene(ThreeDimensionalScene):
  """Scene for a map file: terrain heightmap + surface textures + object meshes."""

  # Flat float32 vertex buffer: [pos(3) + uv_a(2) + uv_b(2)] × N, stride=28
  terrain_vertex_data: Optional[NDArray] = None
  # Flat uint32 index buffer for GL_TRIANGLES
  terrain_index_data: Optional[NDArray] = None
  # 64-element lists: terrain_layer_a[tile] / terrain_layer_b[tile] → 1-based texture slot
  terrain_layer_a: List[int] = field(default_factory=list)
  terrain_layer_b: List[int] = field(default_factory=list)
  # Up to 12 terrain texture slots (raw RGBA bytes, top-to-bottom row order)
  terrain_textures: List[Optional[bytes]] = field(default_factory=list)
  terrain_texture_sizes: List[Tuple[int, int]] = field(default_factory=list)
  lightmap: Optional[bytes] = None
  lightmap_w: int = 0
  lightmap_h: int = 0
  # (H, W) float32 array for camera terrain-floor clamping (not sent to GPU)
  terrain_heights: Optional[NDArray] = None
  # Sky dome meshes loaded from sky.ms1 (empty if not found)
  sky_meshes: List[ViewerMesh] = field(default_factory=list)
