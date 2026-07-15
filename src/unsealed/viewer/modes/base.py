"""
Mode protocol + registry.

A `Mode` bundles everything specific to one scene type (file format family):
its decoder, camera, HUD wiring, and any mode-specific render extensions.
New modes (e.g. .spr, .men) plug in by registering a Mode subclass — no
edits to the core viewer.

Render-phase types live in `rendering/extension.py` so the renderer can use
them without depending on this package; they are re-exported here for
convenience so mode implementations can import everything from one place.

Mode↔Host interactions all flow through `ModeContext` (see `context.py`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Optional, Protocol, runtime_checkable

from ..rendering.extension import RenderExtension, RenderPhase

if TYPE_CHECKING:
  from unsealed.reader.vfs import Resource
  from ..app.world import AppWorld
  from ..camera import Camera
  from ..scenes import ViewerScene
  from .context import ModeContext


__all__ = [
  "AnimationPolicy",
  "BaseMode",
  "MODES",
  "Mode",
  "RenderExtension",
  "RenderPhase",
  "for_path",
  "for_scene",
  "register",
]


@dataclass(frozen=True)
class AnimationPolicy:
  """How AnimationSystem should treat freshly-loaded entities for this mode.

  has_primary    — set `primary_entity` to the first enabled entity
                   (UI-controlled, paused).
  auto_play_all  — every enabled entity starts `playing=True` immediately.

  Modes set the combination that matches their UI semantics. Both False
  means animations are loaded but neither playing nor UI-controlled.
  """

  has_primary: bool = False
  auto_play_all: bool = False


@runtime_checkable
class Mode(Protocol):
  """A pluggable scene-type module.

  One concrete Mode per file format family (model, map, image, …).
  Implementations live under `viewer/modes/<name>/mode.py` and are
  registered in `viewer/modes/__init__.py`.
  """

  name: str
  extensions: tuple[str, ...]  # e.g. (".ms1", ".act")
  scene_type: type["ViewerScene"]  # concrete ViewerScene subclass
  animation_policy: AnimationPolicy

  # ── file → scene ──────────────────────────────────────────────────────────
  def decode(
    self, res: "Resource", shader_cache: Optional[dict] = None
  ) -> "ViewerScene": ...

  # ── app wiring (was SceneConfig) ──────────────────────────────────────────
  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera": ...

  def draw_hud(self, world: "AppWorld") -> None: ...

  def on_key(self, key: int, mctx: "ModeContext") -> None: ...
  def on_mouse_down(
    self, button: int, pos: tuple[int, int], mctx: "ModeContext"
  ) -> None: ...
  def on_mouse_up(
    self, button: int, pos: tuple[int, int], mctx: "ModeContext"
  ) -> None: ...
  def on_mouse_motion(self, dx: int, dy: int, mctx: "ModeContext") -> None: ...
  def on_scroll(
    self, direction: int, mx: int, my: int, mctx: "ModeContext"
  ) -> None: ...

  # ── renderer extensions ───────────────────────────────────────────────────
  def render_extensions(self) -> "Iterable[RenderExtension]": ...


# ── default ABC for mode implementations ───────────────────────────────────


class BaseMode(ABC):
  """Default no-op implementations for optional Mode methods.

  Inherit from this so a concrete mode only overrides what it cares about.
  Class attributes `name`, `extensions`, `scene_type` must be set by subclasses.
  """

  name: str = ""
  extensions: tuple[str, ...] = ()
  scene_type: type = type(None)  # subclasses override
  animation_policy: AnimationPolicy = AnimationPolicy()

  @abstractmethod
  def decode(
    self, res: "Resource", shader_cache: Optional[dict] = None
  ) -> "ViewerScene": ...

  @abstractmethod
  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera": ...

  @abstractmethod
  def draw_hud(self, world: "AppWorld") -> None:
    """Emit this mode's HUD using imgui-bundle widgets.

    Called once per frame between `imgui.new_frame()` and `imgui.render()`.
    Implementations should `imgui.begin(...)` / `imgui.end()` their own
    windows and mutate AppWorld state inline (e.g. on a button click,
    call `world.anim_toggle_play()` directly — no action dispatch).
    """
    ...

  def on_key(self, key: int, mctx: "ModeContext") -> None:
    pass

  def on_mouse_down(
    self, button: int, pos: tuple[int, int], mctx: "ModeContext"
  ) -> None:
    pass

  def on_mouse_up(self, button: int, pos: tuple[int, int], mctx: "ModeContext") -> None:
    pass

  def on_mouse_motion(self, dx: int, dy: int, mctx: "ModeContext") -> None:
    pass

  def on_scroll(self, direction: int, mx: int, my: int, mctx: "ModeContext") -> None:
    pass

  def render_extensions(self) -> "Iterable[RenderExtension]":
    return ()


# ── registry ────────────────────────────────────────────────────────────────

MODES: List[Mode] = []


def register(mode: Mode) -> None:
  """Register a Mode instance. Idempotent on (name, extensions)."""
  for existing in MODES:
    if existing.name == mode.name:
      return
  MODES.append(mode)


def for_path(path: Path) -> Mode:
  """Pick the Mode whose extensions include *path*'s suffix."""
  ext = path.suffix.lower()
  for m in MODES:
    if ext in m.extensions:
      return m
  raise ValueError(f"No registered Mode handles extension {ext!r}")


def for_scene(scene: "ViewerScene") -> Mode:
  """Pick the Mode whose scene_type matches *scene*."""
  for m in MODES:
    if isinstance(scene, m.scene_type):
      return m
  raise ValueError(f"No registered Mode handles scene type {type(scene).__name__}")
