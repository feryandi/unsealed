"""Render extension protocol + phase enum.

Lives in `rendering/` so the renderer can import it without depending on
`modes/`. Mode plugin code re-imports these from `modes.base` for its own
type hints — the names are identical, just hosted at a leaf module.
"""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
  from numpy.typing import NDArray

  from ..scenes import ViewerScene
  from .types import RenderContext


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

  def init(self) -> None: ...
  def upload(self, scene: "ViewerScene") -> None: ...
  def render(self, ctx: "RenderContext", view: "NDArray", proj: "NDArray") -> None: ...
  def free_scene(self) -> None: ...
  def dispose(self) -> None: ...
