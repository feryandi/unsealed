"""
GPU-side data classes and shared constants for the renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray


# Maximum bones supported by the skinning shader.
_MAX_BONES = 128

# Pre-built flat array of _MAX_BONES identity matrices (row-major, ready for GL_TRUE upload).
_IDENTITY_BONE_FLAT = np.tile(np.identity(4, dtype=np.float32).flatten(), _MAX_BONES)

# Vertex buffer strides in bytes.
_STRIDE_PLAIN = 32  # [pos(3) | normal(3) | uv(2)] × 4 bytes
_STRIDE_SKINNED = 64  # [pos(3) | normal(3) | uv(2) | joints(4) | weights(4)] × 4 bytes


class HudAction:
  """Action identifier constants for HudButton.action."""

  OPEN = "open"
  PLAY = "play"
  STOP = "stop"
  SELECT_ANIM = "select_anim"
  TOGGLE_Q3 = "toggle_q3"


@dataclass
class HudButton:
  """
  A clickable button rendered inside a HudPanel.

  icon        : Unicode symbol shown left of the label (empty string = icon-less)
  label       : Short text label
  action      : Action identifier dispatched on click (e.g. "play", "open", "select_anim")
  action_data : Optional payload forwarded to dispatch_action (e.g. animation index)
  rect        : Screen-space (x, y, w, h) in pixels — filled by HudRenderer each frame
  """

  icon: str
  label: str
  action: str
  action_data: Any = None
  rect: Tuple[int, int, int, int] = field(default_factory=lambda: (0, 0, 0, 0))


@dataclass
class HudPanel:
  """
  Describes one HUD text panel.

  x / y are pixel offsets from an edge:
    x >= 0 : offset from left edge
    x <  0 : offset from right edge  (panel right edge is -x pixels from window right)
    y >= 0 : offset from top edge
    y <  0 : offset from bottom edge
  highlight_idx      : index of the line to render in a brighter colour (-1 = none)
  buttons            : horizontal row of HudButton drawn below text lines
  list_items         : vertical list of HudButton drawn below the button row
  list_highlight_idx : index in list_items to highlight as the active selection
  """

  lines: List[str]
  x: int = 10
  y: int = 10
  highlight_idx: int = -1
  buttons: List[HudButton] = field(default_factory=list)
  list_items: List[HudButton] = field(default_factory=list)
  list_highlight_idx: int = -1


@dataclass
class _Q3GpuStage:
  """GPU-side representation of one Q3 shader stage (uploaded texture + blend params)."""
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
    """All per-frame inputs the renderer needs."""

    camera: object  # OrbitCamera | ImageCamera | MapCamera
    width: int
    height: int
    wireframe: bool = False
    bone_matrices: Optional[List[NDArray]] = None
    map_bone_matrices: Optional[Dict[int, List[NDArray]]] = None
    map_node_matrices: Optional[Dict[int, NDArray]] = None
    selected_mesh_idx: Optional[int] = None
    time: float = 0.0
    q3_enabled: bool = True


@dataclass
class _GpuMesh:
  vao: int
  vbo: int
  model_matrix: NDArray  # (4,4) float32, row-major math convention
  is_skinned: bool = False
  instance_vbo: int = 0  # 0 → non-instanced
  instance_count: int = 1
  primitives: List[_GpuPrimitive] = field(default_factory=list)
  # CPU copy of instance matrices kept for animated-skinned-instanced draw path.
  inst_mats_cpu: Optional[NDArray] = None  # shape (N, 4, 4) float32
  # Local-space AABB for CPU ray picking (computed from vertex_data at upload time).
  aabb_min: NDArray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))
  aabb_max: NDArray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))
