"""HudSystem — delegates panel construction to the active Mode."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from ...hud_types import HudPanel
from ..panels import WelcomePanel

if TYPE_CHECKING:
    from ..world import AppWorld


class HudSystem:
    def build(self, world: "AppWorld") -> List[HudPanel]:
        ctx = world.scene.context
        if ctx is None:
            return [WelcomePanel()]
        return ctx.mode.build_hud_panels(world.mode_context())
