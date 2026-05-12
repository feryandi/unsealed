"""
RenderPass — abstract base for all renderer passes.

Each pass is responsible for one stage of the frame pipeline.
Passes are initialized once (init), cleaned up once (cleanup),
and executed every frame (execute).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import moderngl

if TYPE_CHECKING:
  from ..registry import RenderRegistry
  from ..types import PassState, RenderContext


class RenderPass(ABC):
  """Base class for a single stage in the render pipeline."""

  def init(self, mgl: moderngl.Context) -> None:
    """Compile shaders and allocate GPU resources. Called once after GL context is ready."""

  def cleanup(self) -> None:
    """Release all GPU resources owned by this pass."""

  @abstractmethod
  def execute(
    self,
    ctx: "RenderContext",
    state: "PassState",
    registry: "RenderRegistry",
  ) -> None:
    """Run the pass for the current frame."""
