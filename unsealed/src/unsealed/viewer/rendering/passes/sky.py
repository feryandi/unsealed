"""
SkyPass — renders the sky dome (map mode only).

Phase 3.2: init() accepts mgl context (forwarded to SkyRenderer).
"""
from __future__ import annotations

import moderngl

from ..registry import RenderRegistry
from ..sky import SkyRenderer
from ..types import PassState, RenderContext
from .base import RenderPass


class SkyPass(RenderPass):
  """Wraps SkyRenderer as a RenderPass."""

  def __init__(self, sky: SkyRenderer) -> None:
    self._sky = sky

  def init(self, mgl: moderngl.Context) -> None:
    # SkyRenderer.init() is called separately by Renderer.init()
    pass

  def execute(
    self,
    ctx: RenderContext,
    state: PassState,
    registry: RenderRegistry,
  ) -> None:
    self._sky.render(state.view, state.proj, ctx.time)
