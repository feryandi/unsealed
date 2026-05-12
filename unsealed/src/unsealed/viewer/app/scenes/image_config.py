"""ImageConfig — 2-D texture viewer: ImageCamera, image HUD, pan/zoom."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, cast

from .base import SceneConfig

if TYPE_CHECKING:
  from ...app.components.animation import AnimationComponent
  from ...camera import Camera
  from ...rendering import HudPanel
  from ...scenes import ViewerScene
  from ..context import ViewerContext
  from ..world import AppWorld


class ImageConfig(SceneConfig):
  def make_camera(self, scene: "ViewerScene", win_w: int, win_h: int) -> "Camera":
    from ...camera import ImageCamera
    from ...scenes import ImageScene

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
    from ...camera import ImageCamera
    from ...scenes import ImageScene
    from ..panels import ImageControlPanel

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
    from ...camera import ImageCamera

    if any(app._btn):
      cast(ImageCamera, app._camera).pan(dx, dy)

  def on_scroll(self, direction: int, mx: int, my: int, app: "AppWorld") -> None:
    from ...camera import ImageCamera

    cast(ImageCamera, app._camera).zoom_step(direction, mx, my, app._width, app._height)
