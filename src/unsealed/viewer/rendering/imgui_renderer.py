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

import os
from typing import Optional

import pygame
from imgui_bundle import imgui
from imgui_bundle.python_backends.pygame_backend import PygameRenderer

# Korean-capable TTFs, in preference order. Seal Online strings are EUC-KR
# (decoded fine), but imgui's built-in font is ASCII-only, so Korean text
# (e.g. animation names) renders as "?" without a font that has Hangul.
# The default UI font stays the built-in monospace; this font is kept as a
# secondary one that callers push only where Korean appears (animation
# list). imgui 1.92's dynamic atlas rasterizes glyphs on demand — no glyph
# ranges needed.
_FONT_CANDIDATES = (
  r"C:\Windows\Fonts\malgun.ttf",  # Malgun Gothic (Windows Korean UI font)
  r"C:\Windows\Fonts\gulim.ttc",
  r"C:\Windows\Fonts\batang.ttc",
  "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
  "/System/Library/Fonts/AppleSDGothicNeo.ttc",
)
_FONT_SIZE = 16.0


class ImGuiRenderer:
  """Thin wrapper around imgui-bundle's PygameRenderer.

  The pygame backend ships with a VIDEORESIZE handler that re-calls
  `pygame.display.set_mode`, which can disrupt the shared GL context.
  We swallow VIDEORESIZE here and let the caller forward the new size
  via `on_resize` instead.
  """

  def __init__(self) -> None:
    self._impl: Optional[PygameRenderer] = None
    self._korean_font = None  # ImFont | None — pushed only where Korean shows

  def init(self, width: int, height: int) -> None:
    imgui.create_context()
    # Keep the built-in monospace font as the default for all UI; load the
    # Korean font as a secondary one that callers push where needed.
    imgui.get_io().fonts.add_font_default()
    self._korean_font = self._load_korean_font()
    self._impl = PygameRenderer()
    imgui.get_io().display_size = (width, height)

  @property
  def korean_font(self):
    """Hangul-capable ImFont (or None). Push it around Korean text only."""
    return self._korean_font

  @staticmethod
  def _load_korean_font():
    """Load a Hangul-capable font; returns the ImFont (or None)."""
    path = next((p for p in _FONT_CANDIDATES if os.path.exists(p)), None)
    if path is None:
      print("[viewer] no Korean-capable font found; Korean text may show as '?'")
      return None
    try:
      return imgui.get_io().fonts.add_font_from_file_ttf(path, _FONT_SIZE)
    except Exception as e:
      print(f"[viewer] failed to load font {path!r}: {e}")
      return None

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
