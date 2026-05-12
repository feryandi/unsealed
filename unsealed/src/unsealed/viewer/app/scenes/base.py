"""SceneConfig — abstract base for per-scene-type behavior objects."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
  from ...app.components.animation import AnimationComponent
  from ...camera import Camera
  from ...rendering import HudPanel
  from ...scenes import ViewerScene
  from ..context import ViewerContext
  from ..world import AppWorld


class SceneConfig(ABC):
  """Abstract base — one concrete subclass per scene type."""

  @abstractmethod
  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    """Construct and fit a camera for *scene*."""

  @abstractmethod
  def build_hud_panels(
    self,
    ctx: "ViewerContext",
    anim: "AnimationComponent",
    selected_idx: Optional[int],
    q3_enabled: bool = True,
  ) -> "List[HudPanel]":
    """Return the list of HUD panels to display this frame."""

  # Default implementations are no-ops so subclasses override only what they need.

  def on_key(self, key: int, app: "AppWorld") -> None:
    pass

  def on_mouse_down(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None:
    pass

  def on_mouse_up(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None:
    pass

  def on_mouse_motion(self, dx: int, dy: int, app: "AppWorld") -> None:
    pass

  def on_scroll(self, direction: int, mx: int, my: int, app: "AppWorld") -> None:
    pass
