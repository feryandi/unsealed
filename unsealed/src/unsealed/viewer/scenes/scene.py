"""
Viewer intermediate representation.

Sits between the format decoders (pipeline) and the OpenGL renderer.
Contains only plain Python/numpy data — no file handles, no GL objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from numpy.typing import NDArray


@dataclass
class ViewerQ3Stage:
  """One Q3 shader stage resolved to pixel data + GL blend parameters.

  blend_src / blend_dst are raw OpenGL enum ints (stored without importing GL).
  """

  image: Optional[bytes] = None
  image_w: int = 0
  image_h: int = 0
  # animmap: list of (pixels, w, h) per frame; non-empty when stage uses animmap
  anim_frames: List[Tuple[bytes, int, int]] = field(default_factory=list)
  anim_fps: float = 0.0
  blend_src: int = 1  # GL_ONE
  blend_dst: int = 0  # GL_ZERO
  tc_mods: List[Tuple[str, Tuple[float, ...]]] = field(default_factory=list)
  tc_gen_env: bool = False


@dataclass
class ViewerPrimitive:
  """One draw-call worth of index data plus its surface description."""

  indices: NDArray  # uint16 flat array
  # Raw RGBA pixels, top-to-bottom row order (natural image convention).
  # None means no texture — use base_color instead.
  image: Optional[bytes] = None
  image_w: int = 0
  image_h: int = 0
  base_color: Tuple[float, float, float, float] = (0.72, 0.72, 0.72, 1.0)
  # If set, this primitive is rendered via the Q3 multi-stage pass instead of
  # the normal opaque/transparent forward paths.
  q3_stages: Optional[List[ViewerQ3Stage]] = None
  # True when the Q3 shader has `cull disable` / `cull none` — render both sides.
  two_sided: bool = False
  # True when the Q3 shader uses `deformVertexes autosprite` — quad always faces camera.
  is_billboard: bool = False


@dataclass
class ViewerMesh:
  """One mesh: interleaved GPU-ready vertex buffer + one primitive per sub-material.

  Animation membership (skeleton + animation_groups) and origin (source_file)
  live on the owning AnimatedEntity, not on the mesh — a mesh is a pure
  geometry container.
  """

  name: str
  # float32, interleaved layout:
  #   non-skinned: [pos(3), normal(3), uv(2)]                        × n  stride=32
  #   skinned:     [pos(3), normal(3), uv(2), joints(4), weights(4)] × n  stride=64
  vertex_data: NDArray
  # Row-major 4×4 float32 transform matrix (numpy convention)
  model_matrix: NDArray
  primitives: List[ViewerPrimitive] = field(default_factory=list)
  is_skinned: bool = False
  # If set, mesh is drawn via glDrawElementsInstanced.
  # Shape (N, 4, 4) float32 row-major — one world transform per instance.
  instance_matrices: Optional[NDArray] = None
  # Parent mesh name (from ms1 hierarchy). None for root meshes.
  parent_name: Optional[str] = None
  # Local transform relative to the parent mesh — inv(parent_world) @ child_world.
  # None for root meshes (use model_matrix directly).
  local_model_matrix: Optional[NDArray] = None

  @property
  def bind_model_matrix(self) -> NDArray:
    """Return local_model_matrix if set, otherwise model_matrix (bind pose)."""
    return (
      self.local_model_matrix
      if self.local_model_matrix is not None
      else self.model_matrix
    )


@dataclass
class ViewerKeyframe:
  """A single animation keyframe with time in seconds."""

  time: float  # seconds
  value: NDArray  # (3,) for translation/scale, (4,) for rotation [x,y,z,w]


@dataclass
class ViewerBoneAnimation:
  """All keyframe tracks for one bone within an animation group."""

  bone_name: str
  translations: List[ViewerKeyframe] = field(default_factory=list)
  rotations: List[ViewerKeyframe] = field(default_factory=list)
  scales: List[ViewerKeyframe] = field(default_factory=list)


@dataclass
class ViewerAnimationGroup:
  """A named animation ('action') containing per-bone animation tracks."""

  name: str
  bone_animations: List[ViewerBoneAnimation] = field(default_factory=list)
  duration: float = 0.0  # seconds


@dataclass
class ViewerBone:
  """Descriptor for one skeleton bone."""

  name: str
  parent: Optional[str]
  # inv(bind_world_matrix) — (4,4) float32, row-major numpy convention
  inverse_bind: NDArray
  # Bind-pose world TRS — used as defaults when an animation track is empty
  bind_rot: NDArray  # quaternion [x,y,z,w], (4,) float32
  bind_sca: NDArray  # scale,                (3,) float32


@dataclass
class ViewerSkeleton:
  """
  Ordered list of bones for skinning.

  bones is ordered by insertion order of skeleton.bones (a dict), which
  matches the physique bone indices stored in ViewerMesh.vertex_data.
  """

  bones: List[ViewerBone] = field(default_factory=list)
  # Maps bone_name (and bone_name.lower()) → index in bones list
  name_to_idx: Dict[str, int] = field(default_factory=dict)
