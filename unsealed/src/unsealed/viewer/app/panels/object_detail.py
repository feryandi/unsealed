from __future__ import annotations

from typing import List, Optional

from ...rendering import HudPanel
from ...rendering.types import _STRIDE_PLAIN, _STRIDE_SKINNED
from ...scenes import AnimatedEntity, ViewerMesh


class ObjectDetailPanel(HudPanel):
  """Right-side panel showing geometry stats for the currently selected map object.

  The owning AnimatedEntity provides source-file label and animation info
  (those fields moved off ViewerMesh in the Phase 3 entity refactor).
  """

  def __init__(self, mesh: ViewerMesh, entity: Optional[AnimatedEntity] = None) -> None:
    stride = (_STRIDE_SKINNED if mesh.is_skinned else _STRIDE_PLAIN) // 4
    vertex_count = len(mesh.vertex_data) // stride
    tri_count = sum(len(p.indices) // 3 for p in mesh.primitives)
    instance_count = (
      len(mesh.instance_matrices) if mesh.instance_matrices is not None else 1
    )
    file_label = (
      entity.source_file if entity is not None and entity.source_file else mesh.name
    )

    lines: List[str] = [
      "[ Selected Object ]",
      f"  File      : {file_label}",
      f"  Mesh      : {mesh.name}",
      f"  Vertices  : {vertex_count:,}",
      f"  Triangles : {tri_count:,}",
      f"  Instances : {instance_count}",
    ]
    if entity is not None and entity.animation_groups:
      anim_type = "Skinned" if mesh.is_skinned else "Node-anim"
      lines.append(f"  Animated  : {anim_type}")
      for ag in entity.animation_groups:
        lines.append(f"    • {ag.name}  ({ag.duration:.2f}s)")
    else:
      lines.append("  Animated  : No")
    lines += ["", "  Click same object to deselect"]

    super().__init__(lines=lines, x=-10, y=10)
