"""ModeContext — explicit Mode↔Host API.

Wraps AppWorld so Mode implementations see an explicit, narrow interface
to the application state and capabilities they're allowed to touch. The
dataclass is constructed fresh by `AppWorld.mode_context()` for each
event/frame; modes read fields and call methods for state changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

if TYPE_CHECKING:
  from ..app.components.animation import AnimationComponent
  from ..app.context import ViewerContext
  from ..app.world import AppWorld
  from ..camera import Camera


@dataclass
class ModeContext:
  """Host-facing context passed to every Mode method.

  Fields are a snapshot at construction time (read by handlers); state
  changes go through the methods, which forward to the host.
  """

  camera: "Camera"
  width: int
  height: int
  buttons: List[bool]
  lmb_down_pos: Optional[Tuple[int, int]]
  scene_context: Optional["ViewerContext"]
  anim: "AnimationComponent"
  selected_mesh_idx: Optional[int]
  q3_enabled: bool
  wireframe: bool
  selected_shader: Optional[Any]
  shader_scroll: int

  _app: "AppWorld" = field(repr=False)

  # ── mutators / commands ──────────────────────────────────────────────────

  def toggle_wireframe(self) -> None:
    self._app.render.wireframe = not self._app.render.wireframe

  def set_lmb_down(self, pos: Optional[Tuple[int, int]]) -> None:
    self._app.inp.lmb_down_pos = pos

  def set_capture(self, on: bool) -> None:
    self._app.set_capture(on)

  def pick(self, mx: int, my: int) -> None:
    self._app.pick_at(mx, my)

  def open_inject_dialog(self) -> None:
    self._app.open_inject_dialog()

  def anim_toggle_play(self) -> None:
    self._app.anim_toggle_play()

  def anim_stop(self) -> None:
    self._app.anim_stop()

  def anim_select(self, idx: int) -> None:
    self._app.anim_select(idx)

  def anim_scrub(self, delta: float) -> None:
    self._app.anim_scrub(delta)
