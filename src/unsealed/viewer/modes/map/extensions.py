"""
Map-mode RenderExtensions: sky dome (BACKGROUND phase) + terrain (FORWARD_OPAQUE).

These wrap the low-level SkyRenderer / TerrainRenderer and adapt them to the
RenderExtension protocol so the core renderer can drive them through the
generic phase loop, with no isinstance(scene, MapScene) checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import RenderPhase
from .grid import GridRenderer
from .sky import SkyRenderer
from .terrain import TerrainRenderer
from .walkability import WalkabilityRenderer

if TYPE_CHECKING:
  from numpy.typing import NDArray

  from ...rendering import RenderContext
  from ...scenes import ViewerScene


class SkyExtension:
  """Sky dome — renders before opaque geometry in the BACKGROUND phase."""

  phase = RenderPhase.BACKGROUND

  def __init__(self) -> None:
    self._sky = SkyRenderer()

  def init(self) -> None:
    self._sky.init()

  def upload(self, scene: "ViewerScene") -> None:
    # MapMode owns this extension, so scene is always a MapScene here.
    sky_meshes = getattr(scene, "sky_meshes", [])
    self._sky.upload(sky_meshes)

  def render(self, ctx: "RenderContext", view: "NDArray", proj: "NDArray") -> None:
    self._sky.render(view, proj, ctx.time)

  def free_scene(self) -> None:
    self._sky.free_scene()

  def dispose(self) -> None:
    self._sky.cleanup()


class TerrainExtension:
  """Heightmap terrain — forward opaque draw, runs after sky."""

  phase = RenderPhase.FORWARD_OPAQUE

  def __init__(self) -> None:
    self._terrain = TerrainRenderer()

  def init(self) -> None:
    self._terrain.init()

  def upload(self, scene: "ViewerScene") -> None:
    # MapMode owns this extension, so scene is always a MapScene here.
    from .scene import MapScene

    if isinstance(scene, MapScene):
      self._terrain.upload(scene)

  def render(self, ctx: "RenderContext", view: "NDArray", proj: "NDArray") -> None:
    self._terrain.render(view, proj)

  def free_scene(self) -> None:
    self._terrain.free_scene()

  def dispose(self) -> None:
    self._terrain.cleanup()


class WalkabilityExtension:
  """Translucent red overlay on tiles marked as blocked in the walkability grid.

  Phase OVERLAY (before grid extension below), so the colored region sits
  on top of terrain/objects but the grid lines can still layer over it.
  """

  phase = RenderPhase.OVERLAY

  def __init__(self) -> None:
    self._walk = WalkabilityRenderer()
    self._scene: "ViewerScene" = None  # type: ignore[assignment]

  def init(self) -> None:
    self._walk.init()

  def upload(self, scene: "ViewerScene") -> None:
    from .scene import MapScene

    self._scene = scene
    if isinstance(scene, MapScene):
      self._walk.upload(scene)

  def render(self, ctx: "RenderContext", view: "NDArray", proj: "NDArray") -> None:
    from .scene import MapScene

    scene = self._scene
    if not isinstance(scene, MapScene) or not scene.walkability_enabled:
      return
    self._walk.render(view, proj)

  def free_scene(self) -> None:
    self._walk.free_scene()
    self._scene = None  # type: ignore[assignment]

  def dispose(self) -> None:
    self._walk.cleanup()


class GridExtension:
  """512×512 grid overlay following the terrain surface, with selected-cell highlight.

  Runs in OVERLAY so it draws on top of objects too — the grid stays
  visible no matter what's in front. The grid follows the heightmap so
  cells trace the actual surface. Toggleable via `MapScene.grid_enabled`.
  """

  phase = RenderPhase.OVERLAY

  def __init__(self) -> None:
    self._grid = GridRenderer()
    self._scene: "ViewerScene" = None  # type: ignore[assignment]

  def init(self) -> None:
    self._grid.init()

  def upload(self, scene: "ViewerScene") -> None:
    from .scene import MapScene

    self._scene = scene
    if isinstance(scene, MapScene):
      self._grid.upload(scene)

  def render(self, ctx: "RenderContext", view: "NDArray", proj: "NDArray") -> None:
    from .scene import MapScene

    scene = self._scene
    if not isinstance(scene, MapScene) or not scene.grid_enabled:
      return
    self._grid.render(view, proj, scene.selected_grid_cell)

  def free_scene(self) -> None:
    self._grid.free_scene()
    self._scene = None  # type: ignore[assignment]

  def dispose(self) -> None:
    self._grid.cleanup()
