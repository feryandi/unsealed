"""
TerrainPass — forward terrain render (map mode only).

Phase 3.2: init() accepts mgl context (forwarded to TerrainRenderer).
"""
from __future__ import annotations

import moderngl

from ..registry import RenderRegistry
from ..terrain import TerrainRenderer
from ..types import PassState, RenderContext
from .base import RenderPass


class TerrainPass(RenderPass):
  """Wraps TerrainRenderer as a RenderPass."""

  def __init__(self, terrain: TerrainRenderer) -> None:
    self._terrain = terrain

  def init(self, mgl: moderngl.Context) -> None:
    # TerrainRenderer.init() is called separately by Renderer.init()
    pass

  def execute(
    self,
    ctx: RenderContext,
    state: PassState,
    registry: RenderRegistry,
  ) -> None:
    self._terrain.render(state.view, state.proj)
