"""
Mode protocol + registry.

A `Mode` bundles everything specific to one scene type (file format family):
its decoder, camera, HUD wiring, and any mode-specific render extensions.
New modes (e.g. .spr, .men) plug in by registering a Mode subclass — no
edits to the core viewer.

`RenderPhase` and `RenderExtension` are the plug points for mode-specific
draw passes (e.g. terrain + sky for map mode). The renderer iterates
phases in order and runs registered extensions at each phase. Phase 1
defines the shape; the renderer still uses its inline branches until
Phase 2 wires extensions in.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
  from numpy.typing import NDArray

  from ..app.components.animation import AnimationComponent
  from ..app.context import ViewerContext
  from ..app.world import AppWorld
  from ..camera import Camera
  from ..rendering import HudPanel, RenderContext
  from ..scenes import ViewerScene


class RenderPhase(IntEnum):
  """Ordered draw phases the core renderer iterates each frame.

  Mode-supplied `RenderExtension`s declare a phase; the renderer runs them
  at the right time relative to its built-in passes.
  """
  BACKGROUND     = 10  # sky dome, environment (after deferred lighting + depth blit)
  FORWARD_OPAQUE = 20  # terrain or other forward opaque geometry
  FORWARD_Q3     = 30  # core: Q3 multi-stage shaders
  TRANSPARENT    = 40  # core: alpha-blend pass
  OVERLAY        = 50  # core: wireframe, selection highlight


@runtime_checkable
class RenderExtension(Protocol):
  """A mode-provided draw step plugged into a specific RenderPhase.

  Lifecycle (driven by the core Renderer):
    init()              — once, after GL context is ready (compile shaders)
    upload(scene)       — once per file load, when this extension is active
    render(ctx, …)      — every frame, at this extension's phase
    free_scene()        — when a different scene loads (release per-scene GPU state)
    dispose()           — at Renderer.cleanup() (release everything incl. shaders)
  """
  phase: RenderPhase

  def init(self) -> None:
    """Compile shaders / allocate one-time GL state. GL context must be active."""
    ...

  def upload(self, scene: "ViewerScene") -> None:
    """Upload per-scene GPU resources (VAOs, textures)."""
    ...

  def render(self, ctx: "RenderContext", view: "NDArray", proj: "NDArray") -> None:
    """Draw this extension's contribution. view/proj are already mirror-x-adjusted."""
    ...

  def free_scene(self) -> None:
    """Release per-scene GPU state. Keep one-time resources from init()."""
    ...

  def dispose(self) -> None:
    """Release ALL GPU resources owned by this extension."""
    ...


@runtime_checkable
class Mode(Protocol):
  """A pluggable scene-type module.

  One concrete Mode per file format family (model, map, image, …).
  Implementations live under `viewer/modes/<name>/mode.py` and are
  registered in `viewer/modes/__init__.py`.
  """
  name: str
  extensions: tuple[str, ...]      # e.g. (".ms1", ".act")
  scene_type: type["ViewerScene"]  # concrete ViewerScene subclass

  # ── file → scene ──────────────────────────────────────────────────────────
  def decode(self, path: Path, shader_cache: Optional[dict] = None) -> "ViewerScene":
    ...

  # ── app wiring (was SceneConfig) ──────────────────────────────────────────
  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    ...

  def build_hud_panels(
    self,
    ctx: "ViewerContext",
    anim: "AnimationComponent",
    selected_idx: Optional[int],
    q3_enabled: bool = True,
  ) -> "List[HudPanel]":
    ...

  def on_key(self, key: int, app: "AppWorld") -> None: ...
  def on_mouse_down(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None: ...
  def on_mouse_up(self, button: int, pos: tuple[int, int], app: "AppWorld") -> None: ...
  def on_mouse_motion(self, dx: int, dy: int, app: "AppWorld") -> None: ...
  def on_scroll(self, direction: int, mx: int, my: int, app: "AppWorld") -> None: ...

  # ── renderer extensions (Phase 2 wires these in) ──────────────────────────
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

  @abstractmethod
  def decode(self, path: Path, shader_cache: Optional[dict] = None) -> "ViewerScene":
    ...

  @abstractmethod
  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    ...

  @abstractmethod
  def build_hud_panels(
    self,
    ctx: "ViewerContext",
    anim: "AnimationComponent",
    selected_idx: Optional[int],
    q3_enabled: bool = True,
  ) -> "List[HudPanel]":
    ...

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
