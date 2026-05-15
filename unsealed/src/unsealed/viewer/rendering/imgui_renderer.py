"""ImGui renderer wrapper — bridges pygame + the existing GL context to
imgui-bundle's PygameRenderer.

Lifecycle (driven from `viewer_app.py`):
    renderer.init(w, h)               once after pygame.display.set_mode
    for each frame:
      for each pygame event:
        if renderer.process_event(ev) and renderer.want_capture_*:
          # imgui consumed it — don't forward to mode handlers
          continue
        # mode/world handles the event
      renderer.new_frame()            once per frame, before any UI calls
      mode.draw_hud(world)            user code draws widgets
      renderer.render()               submits draw data to GL
      pygame.display.flip()
    renderer.shutdown()               at exit
"""

from __future__ import annotations

from typing import Optional

import pygame
from imgui_bundle import imgui
from imgui_bundle.python_backends.pygame_backend import PygameRenderer


class ImGuiRenderer:
  """Thin wrapper around imgui-bundle's PygameRenderer.

  The pygame backend ships with a VIDEORESIZE handler that re-calls
  `pygame.display.set_mode`, which can disrupt the shared GL context.
  We swallow VIDEORESIZE here and let the caller forward the new size
  via `on_resize` instead.
  """

  def __init__(self) -> None:
    self._impl: Optional[PygameRenderer] = None

  def init(self, width: int, height: int) -> None:
    imgui.create_context()
    self._impl = PygameRenderer()
    imgui.get_io().display_size = (width, height)

  def process_event(self, event: pygame.event.Event) -> bool:
    """Feed one pygame event to imgui. Returns True if imgui consumed it."""
    if self._impl is None or event.type == pygame.VIDEORESIZE:
      return False
    return bool(self._impl.process_event(event))

  def on_resize(self, width: int, height: int) -> None:
    """Notify imgui of a window resize. The caller already updated the
    pygame display mode + GL viewport; this just refreshes io.display_size."""
    if self._impl is None:
      return
    imgui.get_io().display_size = (width, height)

  def new_frame(self) -> None:
    if self._impl is None:
      return
    self._impl.process_inputs()
    imgui.new_frame()

  def render(self) -> None:
    if self._impl is None:
      return
    imgui.render()
    self._impl.render(imgui.get_draw_data())

  def shutdown(self) -> None:
    if self._impl is None:
      return
    self._impl.shutdown()
    self._impl = None
    try:
      imgui.destroy_context()
    except Exception:
      pass

  @property
  def want_capture_mouse(self) -> bool:
    """True when imgui has the mouse — caller must NOT forward mouse
    events (drag, click, wheel) to mode handlers this frame."""
    if self._impl is None:
      return False
    return bool(imgui.get_io().want_capture_mouse)

  @property
  def want_capture_keyboard(self) -> bool:
    """True when imgui has keyboard focus (e.g. a text input is active).
    Caller must NOT forward key events to mode handlers."""
    if self._impl is None:
      return False
    return bool(imgui.get_io().want_capture_keyboard)
