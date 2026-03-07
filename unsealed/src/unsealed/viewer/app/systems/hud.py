"""HudSystem — delegates panel construction to the active SceneConfig."""

from __future__ import annotations

from typing import List

from ...rendering import HudPanel
from ..components.scene_state import SceneComponent
from ..panels import WelcomePanel


class HudSystem:
    def build(self, scene: SceneComponent, q3_enabled: bool = True) -> List[HudPanel]:
        if scene.context is None:
            return [WelcomePanel()]
        return scene.context.config.build_hud_panels(
            scene.context, scene.anim, scene.selected_mesh_idx, q3_enabled
        )
