"""InputSystem — pygame event loop and keyboard/mouse dispatch."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame
from OpenGL.GL import glViewport
from pygame.locals import K_ESCAPE, K_o, MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION

from ..components.input_state import InputComponent

if TYPE_CHECKING:
    from ..world import AppWorld


class InputSystem:
    def process(self, world: "AppWorld") -> None:
        ctx = world.scene.context
        inp = world.inp
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                world.window.running = False

            elif ev.type == pygame.VIDEORESIZE:
                world.window.width, world.window.height = ev.w, ev.h
                glViewport(0, 0, ev.w, ev.h)

            elif ev.type == pygame.KEYDOWN:
                self._on_key(ev.key, world)

            elif ev.type == MOUSEBUTTONDOWN:
                if ev.button in (4, 5):
                    direction = 1 if ev.button == 4 else -1
                    if ctx is not None:
                        ctx.mode.on_scroll(direction, *pygame.mouse.get_pos(), world.mode_context())
                elif self._dispatch_hud_click(ev.pos, world):
                    pass  # HUD button consumed the click; don't update btn state or notify scene
                else:
                    btn_idx = ev.button - 1
                    if 0 <= btn_idx <= 2:
                        inp.btn[btn_idx] = True
                    if ctx is not None:
                        ctx.mode.on_mouse_down(ev.button, ev.pos, world.mode_context())

            elif ev.type == MOUSEBUTTONUP:
                btn_idx = ev.button - 1
                if 0 <= btn_idx <= 2:
                    inp.btn[btn_idx] = False
                if ctx is not None:
                    ctx.mode.on_mouse_up(ev.button, ev.pos, world.mode_context())

            elif ev.type == MOUSEMOTION:
                dx, dy = ev.rel
                if dx == 0 and dy == 0:
                    continue
                if ctx is not None:
                    ctx.mode.on_mouse_motion(dx, dy, world.mode_context())

    def _on_key(self, key: int, world: "AppWorld") -> None:
        if key == K_ESCAPE:
            if world.inp.captured:
                self.set_capture(world.inp, False)
                world.inp.btn[2] = False
            else:
                world.window.running = False
        elif key == K_o:
            world.open_dialog()
        elif world.scene.context is not None:
            world.scene.context.mode.on_key(key, world.mode_context())

    @staticmethod
    def _dispatch_hud_click(pos: tuple, world: "AppWorld") -> bool:
        """Return True and dispatch the action if pos hits any HUD button."""
        mx, my = pos
        for btn in world.render.hud_buttons:
            bx, by, bw, bh = btn.rect
            if bx <= mx < bx + bw and by <= my < by + bh:
                world.dispatch_action(btn.action, btn.action_data)
                return True
        return False

    @staticmethod
    def set_capture(inp: InputComponent, on: bool) -> None:
        """Hide cursor and lock mouse to window."""
        if on == inp.captured:
            return
        inp.captured = on
        pygame.mouse.set_visible(not on)
        pygame.event.set_grab(on)
