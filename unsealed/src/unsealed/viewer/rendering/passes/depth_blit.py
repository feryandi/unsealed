"""
DepthBlitPass — copies the G-Buffer depth attachment to the default FBO.

Must run after GBufferPass so forward passes (terrain, transparent,
Q3 stages) depth-test correctly against opaque geometry.

Phase 3.2: init() accepts mgl context (no GL resources owned here).
"""
from __future__ import annotations

import moderngl

from ..registry import RenderRegistry
from ..types import PassState, RenderContext
from .base import RenderPass
from .gbuffer import GBufferPass


class DepthBlitPass(RenderPass):
  """Blits the G-Buffer depth to the default framebuffer."""

  def __init__(self, gbuffer: GBufferPass) -> None:
    self._gbuffer = gbuffer

  def init(self, mgl: moderngl.Context) -> None:
    pass  # no resources owned by this pass

  def execute(
    self,
    ctx: RenderContext,
    state: PassState,
    registry: RenderRegistry,
  ) -> None:
    self._gbuffer.blit_depth(ctx.width, ctx.height)
