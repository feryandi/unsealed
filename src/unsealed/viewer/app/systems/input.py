"""InputSystem — pygame event loop + keyboard/mouse dispatch.

Per event:
  1. Feed it to imgui first.
  2. If imgui has captured the mouse (over an imgui window) or keyboard
     (text input focused), DROP the event — don't propagate to camera /
     mode handlers. This is what keeps a drag-over-a-panel from also
     panning the scene.
  3. Otherwise dispatch to the active Mode's on_* handlers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame
from OpenGL.GL import glViewport
from pygame.locals import K_ESCAPE, K_o, MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION

from ..components.input_state import InputComponent

if TYPE_CHECKING:
    from ..world import AppWorld


_MOUSE_EVENTS = {MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION, pygame.MOUSEWHEEL}
_KEY_EVENTS = {pygame.KEYDOWN, pygame.KEYUP}


class InputSystem:
    def process(self, world: "AppWorld") -> None:
        ctx = world.scene.context
        inp = world.inp
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                world.window.running = False
                continue

            if ev.type == pygame.VIDEORESIZE:
                world.window.width, world.window.height = ev.w, ev.h
                glViewport(0, 0, ev.w, ev.h)
                world.imgui.on_resize(ev.w, ev.h)
                continue

            # Hand the event to imgui first. PygameRenderer reads it into
            # its IO state regardless of capture — capture only affects
            # whether we forward it onward to mode handlers below.
            world.imgui.process_event(ev)

            if ev.type in _MOUSE_EVENTS and world.imgui.want_capture_mouse:
                # ImGui is over a window — eat the event.
                continue
            if ev.type in _KEY_EVENTS and world.imgui.want_capture_keyboard:
                continue

            if ev.type == pygame.KEYDOWN:
                self._on_key(ev.key, world)

            elif ev.type == MOUSEBUTTONDOWN:
                if ev.button in (4, 5):
                    direction = 1 if ev.button == 4 else -1
                    mx, my = pygame.mouse.get_pos()
                    if ctx is not None:
                        ctx.mode.on_scroll(direction, mx, my, world.mode_context())
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
    def set_capture(inp: InputComponent, on: bool) -> None:
        """Hide cursor and lock mouse to window."""
        if on == inp.captured:
            return
        inp.captured = on
        pygame.mouse.set_visible(not on)
        pygame.event.set_grab(on)
