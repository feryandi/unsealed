from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ...hud_types import HudAction, HudButton, HudPanel
from ...scenes import AnimatedEntity, ViewerMesh
from ...scenes.scene import _STRIDE_PLAIN, _STRIDE_SKINNED
from ...shader.parser import Q3Shader
from .scene import MapScene

# Hard cap on a single visible line's character width inside the shader-detail
# scroll buffer. Q3 .sha files are usually short per line, but a malformed file
# could contain a multi-kilobyte single line; capping here keeps the HUD's
# glTexImage2D from being asked to allocate a gigabyte-sized panel texture.
_SHADER_LINE_CHAR_CAP = 120
# Number of raw-text lines visible at once in the shader-detail panel.
_SHADER_VISIBLE_LINES = 10


class ObjectDetailPanel(HudPanel):
  """Right-side panel showing geometry stats for the currently selected map object.

  Each shader attached to a primitive is rendered as a clickable list-item
  button (action = SELECT_SHADER, data = the Q3Shader instance). Clicking
  opens a ShaderDetailPanel with the shader's raw text scrollably.
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

    list_items: List[HudButton] = []
    if mesh.primitives:
      shaders: List[Q3Shader] = [
        p.shader for p in mesh.primitives if getattr(p, "shader", None) is not None
      ]
      seen_ids: set = set()
      unique_shaders: List[Q3Shader] = []
      for s in shaders:
        if id(s) in seen_ids:
          continue
        seen_ids.add(id(s))
        unique_shaders.append(s)
      if unique_shaders:
        lines.append("")
        lines.append("  Shaders (click for detail):")
        for s in unique_shaders:
          list_items.append(
            HudButton(
              icon="",
              label=s.name,
              action=HudAction.SELECT_SHADER,
              action_data=s,
            )
          )

    super().__init__(lines=lines, x=-10, y=10, list_items=list_items)


class ShaderDetailPanel(HudPanel):
  """Scrollable panel showing one shader's raw text. Stacks under ObjectDetailPanel.

  `shader.raw` can be a multi-kilobyte multi-line blob. We split on newlines,
  clip each visible line to `_SHADER_LINE_CHAR_CAP` characters, and only emit
  the `_SHADER_VISIBLE_LINES`-long window starting at `scroll_offset` so the
  texture stays a bounded size regardless of file size.

  Sets `scroll_action=SCROLL_SHADER`; InputSystem dispatches that with `+1 / -1`
  data when the mouse wheel turns while hovering inside this panel's rect.
  """

  def __init__(self, shader: Q3Shader, scroll_offset: int, anchor_y: int) -> None:
    raw_lines = (shader.raw or "").splitlines() or ["(empty)"]
    total = len(raw_lines)
    max_scroll = max(0, total - _SHADER_VISIBLE_LINES)
    offset = max(0, min(scroll_offset, max_scroll))

    visible = raw_lines[offset : offset + _SHADER_VISIBLE_LINES]
    clipped = [
      (
        ln
        if len(ln) <= _SHADER_LINE_CHAR_CAP
        else ln[: _SHADER_LINE_CHAR_CAP - 1] + "…"
      )
      for ln in visible
    ]

    header = [
      f"[ Shader: {shader.name} ]",
      f"  lines {offset + 1}-{offset + len(clipped)} / {total}",
      "",
    ]

    super().__init__(
      lines=header + clipped,
      x=-10,
      y=anchor_y,
      buttons=[
        HudButton("▲", "Up", HudAction.SCROLL_SHADER, action_data=-1),
        HudButton("▼", "Down", HudAction.SCROLL_SHADER, action_data=+1),
        HudButton("✕", "Close", HudAction.CLOSE_SHADER),
      ],
      scroll_action=HudAction.SCROLL_SHADER,
    )


class MapControlPanel(HudPanel):
  def __init__(
    self,
    scene: MapScene,
    path: Path,
    q3_enabled: bool = True,
  ) -> None:
    tex_count = len([t for t in scene.terrain_textures if t is not None])
    shader_label = "Shader: ON" if q3_enabled else "Shader: OFF"
    super().__init__(
      [
        f"File      : {path.name}",
        f"Objects   : {len(scene.meshes)}",
        f"Textures  : {tex_count}/12",
        "",
        "Controls:",
        "  LMB drag            : Pan",
        "  MMB drag            : Pan (grab)",
        "  RMB drag L/R        : Rotate (yaw)",
        "  RMB drag U/D        : Tilt (pitch 15°–75°)",
        "  WASD / Arrows       : Pan",
        "  Scroll              : Zoom (smart pivot)",
        "  O                   : Open file",
        "  I                   : Inject .ms1 at camera target",
        "  Esc                 : Quit",
      ],
      x=10,
      y=10,
      buttons=[
        HudButton("", "Open File", HudAction.OPEN),
        HudButton("", shader_label, HudAction.TOGGLE_Q3),
      ],
    )
