"""
Map-mode RenderExtensions: sky dome (BACKGROUND phase) + terrain (FORWARD_OPAQUE).

These wrap the low-level SkyRenderer / TerrainRenderer and adapt them to the
RenderExtension protocol so the core renderer can drive them through the
generic phase loop, with no isinstance(scene, MapScene) checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import RenderPhase
from .sky import SkyRenderer
from .terrain import TerrainRenderer

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
