"""ImageMode — viewer mode for .tex / .te1 texture files."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Optional, cast

from ..base import BaseMode, RenderExtension
from .camera import ImageCamera
from .extensions import ImageExtension
from .panels import ImageControlPanel
from .pipeline import TexViewerPipeline
from .scene import ImageScene

if TYPE_CHECKING:
  from ...camera import Camera
  from ...hud_types import HudPanel
  from ...scenes import ViewerScene
  from ..context import ModeContext


class ImageMode(BaseMode):
  name = "image"
  extensions = (".tex", ".te1")
  scene_type = ImageScene

  def __init__(self) -> None:
    self._render_extensions: List[RenderExtension] = [ImageExtension()]

  def render_extensions(self) -> "Iterable[RenderExtension]":
    return self._render_extensions

  def decode(
    self, path: Path, shader_cache: Optional[dict] = None
  ) -> "ViewerScene":
    return TexViewerPipeline().run(path)

  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    cam = ImageCamera()
    if isinstance(scene, ImageScene):
      cam.fit_image(scene.image_w, scene.image_h, win_w, win_h)
    return cam

  def build_hud_panels(self, mctx: "ModeContext") -> "List[HudPanel]":
    ctx = mctx.scene_context
    if ctx is None:
      return []
    scene = cast(ImageScene, ctx.scene)
    cam = cast(ImageCamera, ctx.camera)
    return [
      ImageControlPanel(
        filename=ctx.path.name,
        image_w=scene.image_w,
        image_h=scene.image_h,
        zoom_pct=int(cam.zoom * 100),
      )
    ]

  def on_mouse_motion(self, dx: int, dy: int, mctx: "ModeContext") -> None:
    if any(mctx.buttons):
      cast(ImageCamera, mctx.camera).pan(dx, dy)

  def on_scroll(self, direction: int, mx: int, my: int, mctx: "ModeContext") -> None:
    cast(ImageCamera, mctx.camera).zoom_step(
      direction, mx, my, mctx.width, mctx.height
    )
