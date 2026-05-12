"""ImageMode — viewer mode for .tex / .te1 texture files."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, cast

from ..base import BaseMode
from .camera import ImageCamera
from .panels import ImageControlPanel
from .pipeline import TexViewerPipeline
from .scene import ImageScene

if TYPE_CHECKING:
  from ...app.components.animation import AnimationComponent
  from ...app.context import ViewerContext
  from ...app.world import AppWorld
  from ...camera import Camera
  from ...rendering import HudPanel
  from ...scenes import ViewerScene


class ImageMode(BaseMode):
  name = "image"
  extensions = (".tex", ".te1")
  scene_type = ImageScene

  def decode(
    self, path: Path, shader_cache: Optional[dict] = None
  ) -> "ViewerScene":
    return TexViewerPipeline().run(path)

  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    cam = ImageCamera()
    if isinstance(scene, ImageScene):
      cam.fit_image(scene.image_w, scene.image_h, win_w, win_h)
    return cam

  def build_hud_panels(
    self,
    ctx: "ViewerContext",
    anim: "AnimationComponent",
    selected_idx: Optional[int],
    q3_enabled: bool = True,
  ) -> "List[HudPanel]":
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

  def on_mouse_motion(self, dx: int, dy: int, app: "AppWorld") -> None:
    if any(app._btn):
      cast(ImageCamera, app._camera).pan(dx, dy)

  def on_scroll(self, direction: int, mx: int, my: int, app: "AppWorld") -> None:
    cast(ImageCamera, app._camera).zoom_step(
      direction, mx, my, app._width, app._height
    )
