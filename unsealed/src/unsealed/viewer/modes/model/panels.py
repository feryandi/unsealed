from __future__ import annotations

from pathlib import Path
from typing import List

from ...rendering.types import HudAction, HudButton, HudPanel
from .scene import ModelScene


class ModelControlPanel(HudPanel):
  _CONTROLS = [
    "Controls:",
    "  RMB drag   : Orbit (mouse locked)",
    "  LMB drag   : Orbit (mouse free)",
    "  MMB drag   : Pan",
    "  Scroll     : Zoom (smooth)",
    "  R          : Reset camera",
    "  F          : Fit to model",
    "  W          : Toggle wireframe",
    "  O          : Open file",
    "  Esc        : Quit",
  ]

  _ANIM_CONTROLS = [
    "  Space      : Play / Pause",
    "  Backspace  : Stop",
    "  Up / Down  : Change animation",
    "  Left/Right : Scrub (paused)",
  ]

  def __init__(
    self,
    scene: ModelScene,
    path: Path,
    q3_enabled: bool = True,
  ) -> None:
    # A ModelScene always has one entity (built by the model pipeline).
    primary_entity = scene.entities[0] if scene.entities else None
    anim_count = len(primary_entity.animation_groups) if primary_entity is not None else 0

    lines: List[str] = [
      f"File       : {path.name}",
      f"Meshes     : {len(scene.mesh_names)}",
      f"Triangles  : {scene.tri_count:,}",
    ]
    if anim_count:
      lines += [f"Animations : {anim_count}", ""]
      lines += self._ANIM_CONTROLS
    lines += ["", *self._CONTROLS]

    shader_label = "Shader: ON" if q3_enabled else "Shader: OFF"
    super().__init__(
      lines,
      x=10,
      y=10,
      buttons=[
        HudButton("", "Open File", HudAction.OPEN),
        HudButton("", shader_label, HudAction.TOGGLE_Q3),
      ],
    )
