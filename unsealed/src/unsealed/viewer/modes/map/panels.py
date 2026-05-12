from __future__ import annotations

from pathlib import Path

from ...rendering.types import HudAction, HudButton, HudPanel
from .scene import MapScene


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
        "  Esc                 : Quit",
      ],
      x=10,
      y=10,
      buttons=[
        HudButton("", "Open File", HudAction.OPEN),
        HudButton("", shader_label, HudAction.TOGGLE_Q3),
      ],
    )
