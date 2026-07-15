"""
GPU-side data classes and shared constants for the renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray
from unsealed.viewer.camera.base import Camera


# Maximum bones supported by the skinning shader.
_MAX_BONES = 128

# Pre-built flat array of _MAX_BONES identity matrices (row-major, ready
# for GL_TRUE upload).
_IDENTITY_BONE_FLAT = np.tile(np.identity(4, dtype=np.float32).flatten(), _MAX_BONES)


@dataclass
class _Q3GpuStage:
  """One Q3 shader stage on the GPU (uploaded texture + blend params)."""

  tex_id: Optional[int]
  blend_src: int
  blend_dst: int
  tc_mods: List[Tuple[str, Tuple[float, ...]]]
  tc_gen_env: bool
  # animmap: uploaded GL texture IDs per frame; non-empty when stage uses animmap
  anim_tex_ids: List[int] = field(default_factory=list)
  anim_fps: float = 0.0


@dataclass
class _GpuPrimitive:
  ebo: int
  index_count: int
  texture_id: Optional[int]
  base_color: Tuple[float, float, float, float]
  q3_stages: List[_Q3GpuStage] = field(default_factory=list)
  two_sided: bool = False
  is_billboard: bool = False


class ShaderVariant(Enum):
  PLAIN = "plain"
  SKINNED = "skinned"
  INSTANCED = "instanced"


@dataclass
class DrawCommand:
  """One draw call: entity + primitive + fully-resolved model matrix."""

  entity_id: int
  variant: ShaderVariant
  model_matrix: NDArray  # (4,4) float32, inst_mats_cpu[k] already folded in
  primitive_idx: int
  instance_count: int = 1  # >1 only for GL instanced draws (INSTANCED variant)
  bone_matrices_flat: Optional[NDArray] = None
  bone_count: int = 0


@dataclass
class RenderContext:
  """All per-frame inputs the renderer needs.

  `bone_matrices` and `node_matrices` are unified across model/map modes:
  keyed by GLOBAL mesh index (index into `scene.meshes`), produced by
  `AnimationSystem.update()`. A mesh that's not animated this frame simply
  has no entry — the renderer falls back to its static `model_matrix`.
  """

  camera: Camera
  width: int
  height: int
  wireframe: bool = False
  bone_matrices: Dict[int, List[NDArray]] = field(default_factory=dict)
  node_matrices: Dict[int, NDArray] = field(default_factory=dict)
  selected_mesh_idx: Optional[int] = None
  time: float = 0.0
  q3_enabled: bool = True
