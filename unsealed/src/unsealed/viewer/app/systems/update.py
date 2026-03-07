"""UpdateSystem — per-frame camera and animation advancement."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame
from pygame.locals import K_DOWN, K_LEFT, K_RIGHT, K_UP, K_a, K_d, K_s, K_w

from ...camera import MapCamera

if TYPE_CHECKING:
    from ..world import AppWorld


class UpdateSystem:
    def update(self, world: "AppWorld", dt: float) -> None:
        ctx = world.scene.context
        if ctx is None:
            return

        if isinstance(ctx.camera, MapCamera):
            keys = pygame.key.get_pressed()
            pdx = float(keys[K_d] or keys[K_RIGHT]) - float(keys[K_a] or keys[K_LEFT])
            pdz = float(keys[K_s] or keys[K_DOWN]) - float(keys[K_w] or keys[K_UP])
            if pdx != 0.0 or pdz != 0.0:
                ctx.camera.pan_keys(pdx, pdz, dt)

        ctx.camera.update(dt)
        world._anim_sys.update(
            world.scene.anim,
            ctx.scene if ctx is not None else None,
            dt,
        )
